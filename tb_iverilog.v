`timescale 1 ns /  100 ps

module tb();
   

  reg clk;
   reg nreset;
   

   top top (
            .clk(clk),
            .rst(nreset)
            );

   initial begin
      $dumpfile("test.vcd");
      $dumpvars(0,top);
      nreset = 1;
      #50
        nreset = 0;
      
      
      #10000000
        $finish;
      
   end
   
   always begin
      clk = 0;
      #50;
      clk = 1;
      #50;
   end

endmodule
