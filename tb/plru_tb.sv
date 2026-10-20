`timescale 1ns/1ps
`default_nettype none
module plru_tb;
    parameter int unsigned ENTRIES = 4;
    localparam int unsigned INDEX_WIDTH = $clog2(ENTRIES);
    localparam int unsigned STATE_COUNT = 1 << (ENTRIES-1);
    logic clk = 1'b0;
    logic reset = 1'b1, flush = 1'b0, touch = 1'b0;
    logic [INDEX_WIDTH-1:0] touch_index = '0, victim;
    logic [ENTRIES-2:0] preload, expected_state;
    bit completed = 1'b0;
    int unsigned failures = 0, victim_checks = 0, update_checks = 0;
    int unsigned cycles = 0, watchdog = 2000000;
    string inject = "";

    tree_plru #(.ENTRIES(ENTRIES)) dut (.*);
    always #5 clk = ~clk;

    // The oracle eliminates leaf intervals for every node rather than walking a path.
    function automatic int oracle_victim(input logic [ENTRIES-2:0] tree);
        bit [ENTRIES-1:0] candidates;
        int depth, width, first, discarded;
        candidates = '1;
        for (int node = 0; node < ENTRIES-1; node++) begin
            depth = $clog2(node+2)-1;
            width = ENTRIES >> depth;
            first = (node+1-(1 << depth))*width;
            discarded = first + (tree[node] ? 0 : width/2);
            for (int leaf = discarded; leaf < discarded+width/2; leaf++) candidates[leaf] = 0;
        end
        oracle_victim = -1;
        for (int leaf = 0; leaf < ENTRIES; leaf++)
            if (candidates[leaf]) oracle_victim = leaf;
    endfunction

    function automatic logic [ENTRIES-2:0] oracle_update(
        input logic [ENTRIES-2:0] tree, input int leaf);
        int depth, width, first;
        oracle_update = tree;
        for (int node = 0; node < ENTRIES-1; node++) begin
            depth = $clog2(node+2)-1;
            width = ENTRIES >> depth;
            first = (node+1-(1 << depth))*width;
            if (leaf >= first && leaf < first+width)
                oracle_update[node] = leaf < first+width/2;
        end
    endfunction

    task automatic check(input bit good, input string description);
        if (!good) begin
            failures++;
            $fatal(1, "PLRU_CHECK_FAILED %s N=%0d cycle=%0d", description, ENTRIES, cycles);
        end
    endtask

    always @(posedge clk) begin
        cycles <= cycles + 1;
        if (cycles >= watchdog) $fatal(1, "PLRU_WATCHDOG");
    end

    initial begin
        if ($value$plusargs("INJECT=%s", inject)) begin end
        if ($value$plusargs("WATCHDOG=%d", watchdog)) begin end
        if (inject == "timeout") forever @(negedge clk);
        repeat (2) @(negedge clk);
        reset = 0;
        check(dut.state_q === '0 && victim === '0, "reset");
        if (inject == "unexpected") $stop;
        for (int state_number = 0; state_number < STATE_COUNT; state_number++) begin
            for (int leaf = 0; leaf < ENTRIES; leaf++) begin
                @(negedge clk);
                touch = 0;
                preload = (ENTRIES-1)'(state_number);
                force dut.state_q = preload;
                #1;
                if (leaf == 0) begin
                    check(victim === INDEX_WIDTH'(oracle_victim(preload)) &&
                          !(inject == "checker" && state_number == 0), "victim");
                    victim_checks++;
                end
                release dut.state_q;
                touch_index = INDEX_WIDTH'(leaf);
                expected_state = oracle_update(preload, leaf);
                touch = 1;
                @(posedge clk);
                #0.001;
                check(dut.state_q === expected_state, "update");
                check(victim === INDEX_WIDTH'(oracle_victim(expected_state)), "updated victim");
                update_checks++;
            end
        end
        @(negedge clk);
        touch = 0;
        expected_state = dut.state_q;
        repeat (3) @(negedge clk);
        check(dut.state_q === expected_state, "disabled hold");
        flush = 1;
        touch = 1;
        @(negedge clk);
        check(dut.state_q === '0, "flush priority");
        flush = 0;
        reset = 1;
        @(negedge clk);
        check(dut.state_q === '0, "reset priority");
        if (inject == "coverage") victim_checks--;
        check(victim_checks == STATE_COUNT && update_checks == STATE_COUNT*ENTRIES, "coverage");
        completed = 1;
        $display("PLRU_PASS N=%0d states=%0d updates=%0d", ENTRIES, victim_checks, update_checks);
        $finish;
    end
endmodule
`default_nettype wire
