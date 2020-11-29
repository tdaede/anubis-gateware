#!/usr/bin/python3

from nmigen import *
from nmigen_boards.tinyfpga_bx import *
from nmigen.build.dsl import *
from m68krom import M68KROM

class System(Elaboratable):
    def __init__(self):
        self.rom = M68KROM(4, 'exerciser.bin', 0)
        pass

    def elaborate(self, platform):
        m = Module()
        platform.add_resources([
             Resource("data", 0, Pins("1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16", dir="io", conn=("gpio", 0))),
             Resource("addr", 0, Pins("17 18 19 20", dir="i", conn=("gpio", 0)))
        ])
        data_pins = platform.request("data")
        addr_pins = platform.request("addr")
        m.d.comb += self.rom.addr.eq(addr_pins)
        m.d.comb += data_pins.o.eq(self.rom.data)
        m.d.comb += data_pins.oe.eq(0xffff)
        m.submodules += self.rom
        return m

if __name__ == "__main__":
    platform = TinyFPGABXPlatform()
    sys = System()
    platform.build(sys, do_program=True)
