import unittest
from nmigen import *
from nmigen_soc import wishbone
from nmigen.sim import *


# 32 bit wishbone to 16 bit 68000 bus
class WishboneTo68000(Elaboratable):
    def __init__(self, wb, wb_fc, wb_ipl):
        self.wb = wb
        self.wb_fc = wb_fc
        self.wb_ipl = wb_ipl
        self.addr = Signal(23)
        self.fc = Signal(3)
        self.ipl = Signal(3)
        self.o_data = Signal(16)
        self.i_data = Signal(16)
        self.uds_ = Signal(reset = 1)
        self.lds_ = Signal(reset = 1)
        self.as_ = Signal(reset = 1)
        self.rw_ = Signal(reset = 1)
        self.dtack_ = Signal(reset = 1)
        self.br_ = Signal(reset = 1)
        self.bg_ = Signal(reset = 1)
        self.bgack_ = Signal(reset = 1)
        self.bus_assert = Signal(reset = 1)

    def elaborate(self, platform):
        m = Module()
        i_data_high = Signal(16) # register to hold high bytes (low address)
                                 # of 32 bit read
        #m.d.comb += self.rw_.eq(~self.wb.we)
        m.d.comb += self.wb.dat_r.eq(Cat(self.i_data, i_data_high))
        m.d.comb += self.fc.eq(self.wb_fc)
        m.d.comb += self.wb_ipl.eq(self.ipl)
        with m.FSM() as fsm:
            with m.State("WAIT0"):
                m.d.comb += self.as_.eq(1)
                with m.If(self.br_ == 0):
                    m.next = "BUS_GRANT"
                with m.Elif(self.wb.cyc & self.wb.stb):
                    with m.If(self.wb_fc == 0x7):
                        m.next = "ADDR1" # only do a 16 bit read for int ack
                    with m.Elif(self.wb.sel[2] | self.wb.sel[3]):
                        m.next = "ADDR0"
                    with m.Else():
                        m.next = "ADDR1"
            with m.State("ADDR0"):
                m.d.comb += self.addr.eq(self.wb.adr << 1)
                with m.If(self.wb.we):
                    m.next = "STROBE0_W"
                with m.Else():
                    m.next = "STROBE0"
            with m.State("STROBE0_W"):
                m.d.comb += self.addr.eq(self.wb.adr << 1)
                m.d.comb += self.rw_.eq(~self.wb.we)
                m.d.comb += self.as_.eq(0)
                m.next = "STROBE0"
            with m.State("STROBE0"):
                m.d.comb += self.addr.eq(self.wb.adr << 1)
                m.d.comb += self.rw_.eq(~self.wb.we)
                m.d.comb += self.uds_.eq(~self.wb.sel[3])
                m.d.comb += self.lds_.eq(~self.wb.sel[2])
                m.d.comb += self.as_.eq(0)
                m.d.comb += self.o_data.eq(self.wb.dat_w[16:32])
                with m.If(~self.dtack_):
                    m.d.sync += i_data_high.eq(self.i_data)
                    with m.If(self.wb.sel[1] | self.wb.sel[0]):
                        m.next = "ADDR1"
                    with m.Else():
                        m.next = "DTACK1"
            with m.State("ADDR1"):
                with m.If(self.wb.we):
                    m.next = "STROBE1_W"
                with m.Else():
                    m.next = "STROBE1"
            with m.State("STROBE1_W"):
                m.d.comb += self.addr.eq((self.wb.adr << 1) + 1)
                m.d.comb += self.rw_.eq(~self.wb.we)
                m.d.comb += self.as_.eq(0)
                m.next = "STROBE1"
            with m.State("STROBE1"):
                m.d.comb += self.addr.eq((self.wb.adr << 1) + 1)
                m.d.comb += self.rw_.eq(~self.wb.we)
                m.d.comb += self.uds_.eq(~self.wb.sel[1])
                m.d.comb += self.lds_.eq(~self.wb.sel[0])
                m.d.comb += self.as_.eq(0)
                m.d.comb += self.o_data.eq(self.wb.dat_w[0:16])
                with m.If(~self.dtack_):
                    m.next = "DTACK1"
            with m.State("DTACK1"):
                m.d.comb += self.addr.eq((self.wb.adr << 1) + 1)
                m.d.comb += self.wb.ack.eq(1)
                m.next = "WAIT0"
            with m.State("BUS_GRANT"):
                m.d.comb += self.bg_.eq(0)
                m.d.comb += self.bus_assert.eq(0)
                m.next = "BUS_GRANT"
                with m.If(self.br_ == 1):
                    m.next = "WAIT0"
                with m.If(self.bgack_ == 0):
                    m.next = "BUS_GRANT_ACK"
            with m.State("BUS_GRANT_ACK"):
                m.d.comb += self.bus_assert.eq(0)
                m.next = "BUS_GRANT_ACK"
                with m.If(self.bgack_ == 1):
                    m.next = "WAIT0"

        return m

class Test(unittest.TestCase):
    def test_simple(self):
        wb = wishbone.Interface(addr_width = 30, data_width = 32, granularity = 8, features = ["err", "rty", "cti", "bte", "lock"])
        wb_fc = Signal(3)
        wb_ipl = Signal(3)
        dut = WishboneTo68000(wb, wb_fc, wb_ipl)

        def sim_test():
            # test byte reads
            for b in range(0,4):
                yield wb.adr.eq(0x0)
                yield wb.cyc.eq(1)
                yield wb.stb.eq(1)
                yield wb.sel.eq(1 << b)
                yield wb.we.eq(0)
                while ((yield dut.lds_) & (yield dut.uds_)) != 0:
                    yield Tick()
                    yield Delay(1e-9)
                if b > 1:
                    self.assertEqual((yield dut.addr), 0x0)
                else:
                    self.assertEqual((yield dut.addr), 0x1)
                self.assertEqual((yield dut.as_), 0)
                yield dut.i_data.eq((yield dut.addr))
                yield dut.dtack_.eq(0)
                yield Tick()
                yield Delay(1e-9)
                while (yield wb.ack) == 0:
                    yield Tick()
                    yield Delay(1e-9)
                yield wb.cyc.eq(0)
                yield wb.stb.eq(0)
                self.assertEqual((yield dut.as_), 1)
                self.assertEqual((yield dut.lds_), 1)
                self.assertEqual((yield dut.uds_), 1)
                yield Tick()

            # test word reads
            yield wb.adr.eq(0xaaa)
            yield wb.cyc.eq(1)
            yield wb.stb.eq(1)
            yield wb.sel.eq(0xf)
            yield wb.we.eq(0)
            while ((yield dut.lds_) & (yield dut.uds_)) != 0:
                yield Tick()
                yield Delay(1e-9)
            self.assertEqual((yield dut.addr), 0xaaa << 1)
            self.assertEqual((yield dut.as_), 0)
            yield dut.i_data.eq((yield dut.addr))
            yield dut.dtack_.eq(0)
            yield Tick()
            yield Delay(1e-9)
            yield wb.cyc.eq(0)
            yield wb.stb.eq(0)
            self.assertEqual((yield dut.as_), 1)
            self.assertEqual((yield dut.lds_), 1)
            self.assertEqual((yield dut.uds_), 1)
            while ((yield dut.lds_) & (yield dut.uds_)) != 0:
                yield Tick()
                yield Delay(1e-9)
            yield dut.i_data.eq((yield dut.addr))
            while (yield wb.ack) == 0:
                yield Tick()
                yield Delay(1e-9)
            yield Tick()

            # test interrupt
            yield wb.adr.eq(0xfffffff9) # 32 bit level lower 3 bits
            yield wb_ipl.eq(1)
            yield wb_fc.eq(0x7)
            yield wb.cyc.eq(1)
            yield wb.stb.eq(1)
            yield wb.sel.eq(0xf)
            yield wb.we.eq(0)
            while ((yield dut.lds_) & (yield dut.uds_)) != 0:
                yield Tick()
                yield Delay(1e-9)
            self.assertEqual((yield dut.addr), ((0xfffffff9 << 1) + 1) & 0x7fffff)
            self.assertEqual((yield dut.as_), 0)
            yield dut.i_data.eq((yield dut.addr))
            yield dut.dtack_.eq(0)
            yield Tick()
            yield Delay(1e-9)
            yield wb.cyc.eq(0)
            yield wb.stb.eq(0)
            self.assertEqual((yield dut.as_), 1)
            self.assertEqual((yield dut.lds_), 1)
            self.assertEqual((yield dut.uds_), 1)
            yield Tick()


        sim = Simulator(dut)
        sim.add_clock(1e-6)
        sim.add_sync_process(sim_test)
        with sim.write_vcd(vcd_file=open("wb_to_68k.vcd", "w")):
            sim.run()

if __name__ == "__main__":
    test = Test()
    test.test_simple()
