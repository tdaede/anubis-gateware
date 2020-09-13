#include <iostream>
#include <fstream>
#include <backends/cxxrtl/cxxrtl_vcd.h>
#include "top.cpp"
    
using namespace std;
    
int main()
{
  cxxrtl_design::p_anubis top;
  cxxrtl::debug_items all_debug_items;
  top.debug_info(all_debug_items);
  cxxrtl::vcd_writer vcd;
  vcd.timescale(1, "us");
  vcd.add_without_memories(all_debug_items);
  std::ofstream waves("waves_cxxrtl.vcd");
  top.step();
  vcd.sample(0);
    
  bool prev_led = 0;
    
  top.step();
  for(int cycle=0;cycle<1000;++cycle){
    
    top.p_clk.set<bool>(false);
    top.step();
    vcd.sample(cycle*2 + 0);
    top.p_clk.set<bool>(true);
    top.step();
    vcd.sample(cycle*2 + 1);
    waves << vcd.buffer;
    vcd.buffer.clear();
  }
}
