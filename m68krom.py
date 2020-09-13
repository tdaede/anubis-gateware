import unittest
from nmigen import *
from nmigen_soc import wishbone
from nmigen.sim import *

class M68KROM(Elaboratable):
    def __init__(self, addr_width, filename, file_offset):
        self.depth = 2**addr_width
        self.addr = Signal(addr_width)
        self.data = Signal(16)
        f = open(filename, 'rb')
        f.seek(file_offset)
        byte_content = f.read(self.depth)
        dat = [byte_content[i] << 8 | byte_content[i + 1] for i in range(0, self.depth, 2)]
        self.mem = Memory(width=16, depth=self.depth, init=dat)

    def elaborate(self, platform):
        m = Module()
        m.submodules.rdport = rdport = self.mem.read_port()
        m.d.comb += rdport.addr.eq(self.addr)
        m.d.comb += self.data.eq(rdport.data)
        return m

class M68KRAM(Elaboratable):
    def __init__(self, addr_width):
        self.depth = 2**addr_width
        self.addr = Signal(addr_width)
        self.o_data = Signal(16)
        self.i_data = Signal(16)
        self.rw_ = Signal(reset=1)
        self.mem = Memory(width=16, depth=self.depth)

    def elaborate(self, platform):
        m = Module()
        m.submodules.rdport = rdport = self.mem.read_port()
        m.submodules.wrport = wrport = self.mem.write_port()
        m.d.comb += rdport.addr.eq(self.addr)
        m.d.comb += wrport.addr.eq(self.addr)
        m.d.comb += self.o_data.eq(rdport.data)
        m.d.comb += wrport.data.eq(self.i_data)
        m.d.comb += wrport.en.eq(~self.rw_)
        return m

class Test(unittest.TestCase):
    def test_simple(self):
        dut = M68KROM(0x4, '../x68kd11s/iplromxv.dat', 0x10000)

        def sim_test():
            yield dut.addr.eq(0x00000001)
            yield Tick()
            yield Settle()
            self.assertEqual((yield dut.data), 0x2000)

        sim = Simulator(dut)
        sim.add_clock(1e-6)
        sim.add_sync_process(sim_test)
        sim.run()
    def test_ram(self):
        dut = M68KRAM(4)

        def sim_test():
            yield dut.addr.eq(1)
            yield Tick()
            yield Settle()
            self.assertEqual((yield dut.o_data), 0)
            yield dut.addr.eq(0)
            yield dut.rw_.eq(0)
            yield dut.i_data.eq(0xaaaa)
            yield Tick()
            yield dut.addr.eq(1)
            yield dut.rw_.eq(1)
            yield Tick()
            yield Settle()
            self.assertEqual((yield dut.o_data), 0)
            yield dut.addr.eq(0)
            yield dut.rw_.eq(1)
            yield Tick()
            yield Settle()
            self.assertEqual((yield dut.o_data), 0xaaaa)

        sim = Simulator(dut)
        sim.add_clock(1e-6)
        sim.add_sync_process(sim_test)
        sim.run()

if __name__ == "__main__":
    test = Test()
    test.test_simple()
    test.test_ram()
