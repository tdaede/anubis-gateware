#!/usr/bin/python3

from nmigen import *
from nmigen_boards.tinyfpga_bx import *
from nmigen.build.dsl import *

class System(Elaboratable):
    def __init__(self):
        pass

    def elaborate(self, platform):
        m = Module()
        platform.add_resources([
             Resource("data", 0, Pins("1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16", dir="io", conn=("gpio", 0)))
        ])
        data_pins = platform.request("data")
        m.d.comb += data_pins.o.eq(0)
        m.d.comb += data_pins.oe.eq(0xffff)
        return m

if __name__ == "__main__":
    platform = TinyFPGABXPlatform()
    sys = System()
    platform.build(sys, do_program=True)
