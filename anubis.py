#!/usr/bin/env python3

from nmigen import *
from nmigen.cli import main
from nmigen_soc import wishbone
from nmigen_soc.memory import MemoryMap
from nmigen_boards.ulx3s import *
from nmigen.build.dsl import *
from ao68000.nmigen import ao68000soc
from wb_to_68k import WishboneTo68000
from m68krom import M68KROM, M68KRAM

class System(Elaboratable):
    def __init__(self):
        self.ao68000soc = ao68000soc()
        self.wb_to_68k = WishboneTo68000(self.ao68000soc.bus, self.ao68000soc.fc, self.ao68000soc.ipl)
        pass

    def elaborate(self, platform):
        m = Module()
        m.domains.sync = ClockDomain()
        clk25 = platform.request("clk25")
        m.d.comb += ClockSignal().eq(clk25.i)
        #hack for ao68000 to start up correctly
        m.d.comb += ResetSignal().eq(platform.request("button_fire",0))

        platform.add_resources([
            Resource("addr", 0, Pins("24+ 25- 25+ 26- 26+ 27- 27+ 0- 0+ 1- 1+ 2- 2+ 3- 3+ 5+ 6- 6+ 7- 7+ 8- 8+ 9-", dir="io", conn=("gpio", 0))),
            Resource("fc", 0, Pins("5- 4+ 4-", dir="io", conn=("gpio", 0))),
            Resource("data", 0, Pins("20+ 20- 19+ 19- 18+ 18- 17+ 17- 10+ 10- 11+ 11- 12+ 12- 13+ 13-", dir="io", conn=("gpio", 0))),
            #Resource("dtack", 0, Pins("9+", dir="i", conn=("gpio", 0))),
            #Resource("reset", 0, Pins("22+", dir="i", conn=("gpio", 0))),
            # changed: move dtack to reset pin because of oops on rev 1 pcb
            # then use original dtack line as data_dir
            Resource("dtack", 0, Pins("22+", dir="i", conn=("gpio", 0))),
            Resource("data_dir", 0, Pins("9+", dir="o", conn=("gpio", 0))),
            Resource("ipl", 0, Pins("24- 23+ 23-", dir="i", conn=("gpio", 0))),
            Resource("clk", 0, Pins("22-", dir="i", conn=("gpio", 0))),
            Resource("br", 0, Pins("21+", dir="i", conn=("gpio", 0))),
            Resource("bgack", 0, Pins("21-", dir="i", conn=("gpio", 0))),
            # bg goes through an open collector inverter
            Resource("bg", 0, Pins("16+", dir="o", conn=("gpio", 0))),
            # addr_dir: 0 = read, 1 = write
            # controls: addr, fc, as, uds, lds, rw
            Resource("addr_dir", 0, Pins("16-", dir="o", conn=("gpio", 0))),
            Resource("as_", 0, Pins("15+", dir="io", conn=("gpio", 0))),
            Resource("uds_", 0, Pins("15-", dir="io", conn=("gpio", 0))),
            Resource("rw_", 0, Pins("14+", dir="io", conn=("gpio", 0))),
            Resource("lds_", 0, Pins("14-", dir="io", conn=("gpio", 0)))
        ])

        timer  = Signal(24)
        m.d.sync += timer.eq(timer + 1)

        m.submodules.ao68000soc = self.ao68000soc

        m.d.comb += self.wb_to_68k.dtack_.eq(0)
        m.submodules.wb_to_68k = self.wb_to_68k

        plat_data = platform.request("data", 0)
        data_dir = platform.request("data_dir")

        leds = [platform.request("led", i) for i in range(0,8)]
        for i in range(0, 8):
            m.d.comb += leds[i].eq(self.ao68000soc.bus.adr[i+15])

        bus_assert = self.wb_to_68k.bus_assert

        m.d.comb += platform.request("bg").o.eq(~self.wb_to_68k.bg_)

        # section of signals controlled by rw_
        m.d.comb += plat_data.o.eq(self.wb_to_68k.o_data)
        m.d.comb += self.wb_to_68k.i_data.eq(plat_data.i)
        with m.If(~self.wb_to_68k.rw_ & bus_assert):
            m.d.comb += plat_data.oe.eq(0xFFFF)
            m.d.comb += data_dir.o.eq(1)
        with m.Else():
            m.d.comb += plat_data.oe.eq(0)
            m.d.comb += data_dir.o.eq(0)

        # section of signals controlled by bus_assert
        m.d.comb += platform.request("addr_dir").o.eq(bus_assert)
        addr = platform.request("addr", 0)
        fc = platform.request("fc", 0)
        as_ = platform.request("as_")
        uds_ = platform.request("uds_")
        lds_ = platform.request("lds_")
        rw_ = platform.request("rw_")
        m.d.comb += addr.o.eq(self.wb_to_68k.addr)
        m.d.comb += addr.oe.eq(bus_assert)
        m.d.comb += fc.o.eq(self.ao68000soc.fc)
        m.d.comb += fc.oe.eq(bus_assert)
        m.d.comb += as_.o.eq(self.wb_to_68k.as_)
        m.d.comb += as_.oe.eq(bus_assert)
        m.d.comb += uds_.o.eq(self.wb_to_68k.uds_)
        m.d.comb += uds_.oe.eq(bus_assert)
        m.d.comb += lds_.o.eq(self.wb_to_68k.lds_)
        m.d.comb += lds_.oe.eq(bus_assert)
        m.d.comb += rw_.o.eq(self.wb_to_68k.rw_)
        m.d.comb += rw_.oe.eq(bus_assert)

        # temporary hack for led counter
        #m.d.comb += self.wb_to_68k.i_data.eq(0)


        # /----------------------------------------------------------\
        # | RETURN                                                   |
        # \----------------------------------------------------------/
        return m

if __name__ == "__main__":
    platform = ULX3S_85F_Platform()
    sys = System()
    platform.build(sys, do_program=True)
