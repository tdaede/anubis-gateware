#!/usr/bin/env python3

from nmigen import *
from nmigen.cli import main
from nmigen_soc import wishbone
from nmigen_soc.memory import MemoryMap
from ao68000.nmigen import ao68000soc
from wb_to_68k import WishboneTo68000
from m68krom import M68KROM, M68KRAM

#cd_sync = ClockDomain()


#diy wrapper, unused
class AO68000Wrapper(Elaboratable):
    def __init__(self, bus):
        self.bus = bus
        self.nreset = Signal()

    def elaborate(self, platform):
        m = Module()
        m.domains += cd_sync
        m.submodules.cpu = Instance("ao68000",
                                    i_CLK_I = cd_sync.clk,
                                    o_ADR_O = self.bus.adr,
                                    o_DAT_O = self.bus.dat_w,
                                    i_DAT_I = self.bus.dat_r,
                                    o_SEL_O = self.bus.sel,
                                    o_CYC_O = self.bus.cyc,
                                    o_STB_O = self.bus.stb,
                                    o_WE_O = self.bus.we,
                                    i_ACK_I = self.bus.ack,
                                    i_reset_n = self.nreset,
                                    i_ERR_I = 0,
                                    i_RTY_I = 0,
                                    i_ipl_i = 0
        )
        return m

class WishboneROM(Elaboratable):
    def __init__(self):
        self.bus = wishbone.Interface(addr_width = 17, data_width = 8)
        self.bus.memory_map = MemoryMap(addr_width = 17, data_width = 8)
        f = open('../x68kd11s/iplromxv.dat', 'rb')
        dat = f.read()
        self.mem = Memory(width=8, depth=131072, init=dat)

    def elaborate(self, platform):
        m = Module()
        m.submodules.rdport = rdport = self.mem.read_port()
        m.d.comb += rdport.addr.eq(self.bus.adr)
        m.d.comb += self.bus.dat_r.eq(rdport.data)
        with m.If(self.bus.sel):
            m.d.sync += self.bus.ack.eq(1)
        with m.Else():
            m.d.sync += self.bus.ack.eq(0)
        return m

class System(Elaboratable):
    def __init__(self):
        #self.bus_decoder = wishbone.Decoder(addr_width = 30, data_width = 32, granularity = 8, features = ["err", "rty", "cti", "bte", "lock"])
        #self.ao68000wrapper = AO68000Wrapper(bus = self.bus_decoder.bus)
        #self.bus = wishbone.Interface(addr_width = 30, data_width = 32, granularity = 8, features = ["err", "rty", "cti", "bte", "lock"])
        self.ao68000soc = ao68000soc()
        self.addr_byte = Signal(24)
        self.wb_to_68k = WishboneTo68000(self.ao68000soc.bus)
        self.boot_rom = M68KROM(0x4, '../x68kd11s/iplromxv.dat', 0x10000)
        self.ipl_rom = M68KROM(17, '../x68kd11s/iplromxv.dat', 0x0)
        self.ram = M68KRAM(16)
        pass

    def elaborate(self, platform):
        m = Module()
        #rom = WishboneROM()
        #m.submodules.rom = rom
        #self.bus_decoder.add(rom.bus, sparse=True)
        #m.submodules.ao68000wrapper = self.ao68000wrapper
        m.d.comb += self.addr_byte.eq(self.ao68000soc.bus.adr << 2)
        m.d.comb += self.boot_rom.addr.eq(self.wb_to_68k.addr)
        m.d.comb += self.ipl_rom.addr.eq(self.wb_to_68k.addr - (0xfe0000 >> 1))
        m.d.comb += self.ram.addr.eq(self.wb_to_68k.addr)
        m.d.comb += self.wb_to_68k.dtack_.eq(0)
        with m.If(self.wb_to_68k.addr < 4):
            m.d.comb += self.wb_to_68k.i_data.eq(self.boot_rom.data)
        with m.Elif(self.wb_to_68k.addr >= (0xfe0000 >> 1)):
            m.d.comb += self.wb_to_68k.i_data.eq(self.ipl_rom.data)
        with m.Else():
            m.d.comb += self.wb_to_68k.i_data.eq(self.ram.o_data)
        m.d.comb += self.ram.i_data.eq(self.wb_to_68k.o_data)
        with m.If(self.wb_to_68k.addr < (0x800000 >> 1)):
            m.d.comb += self.ram.rw_.eq(self.wb_to_68k.rw_)
        m.submodules.ao68000soc = self.ao68000soc
        m.submodules.wb_to_68k = self.wb_to_68k
        m.submodules.boot_rom = self.boot_rom
        m.submodules.ipl_rom = self.ipl_rom
        m.submodules.ram = self.ram
        #m.submodules.bus_decoder = self.bus_decoder
        return m


if __name__ == "__main__":
    sys = System()
    clk = ClockSignal()
    rst = ResetSignal()
    main(sys, ports=[clk, rst])
