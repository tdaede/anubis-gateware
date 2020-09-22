ALL_PYTHON = wb_to_68k.py m68krom.py ao68000/ao68000/nmigen/ao68000.py

VERILOG_SOURCE = ao68000/ao68000/verilog/ao68000.v ao68000/ao68000/verilog/alu_mult_generic.v ao68000/ao68000/verilog/memory_registers_generic.v

VERILOG_IVERILOG = $(VERILOG_SOURCE) tb_iverilog.v top.v

top.v: $(ALL_PYTHON) anubis_sim.py
	./anubis_sim.py generate -t v > top.v

top.il: $(ALL_PYTHON)
	./anubis_sim.py generate -t il > top.il

a.out: $(VERILOG_IVERILOG)
	iverilog $(VERILOG_IVERILOG)

simulate: a.out
	./a.out

top.cpp: $(VERILOG_SOURCE) top.il
	yosys -p "read_verilog $(VERILOG_SOURCE); read_rtlil top.il; delete w:$$verilog_initial_trigger; write_cxxrtl top.cpp"

tb: top.cpp main.cpp
	c++ -g -O3 -std=c++14 -I `yosys-config --datdir`/include main.cpp -o tb

cxxrtl: tb
	./tb

PHONY: simulate cxxrtl
