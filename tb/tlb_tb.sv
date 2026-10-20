`timescale 1ns/1ps
`default_nettype none
module tlb_tb;
    import vm_pkg::*;
    parameter int unsigned ENTRIES = 4;
    logic clk = 0, reset = 1, flush = 0, lookup_touch = 0, fill_valid = 0;
    vpn_t lookup_vpn = 0, fill_vpn = 0;
    ppn_t lookup_ppn, fill_ppn = 0;
    flags_t lookup_flags, fill_flags = flags_t'(8'hdf);
    logic lookup_hit;
    bit completed = 0;
    int unsigned failures = 0, checks = 0;
    typedef struct packed {logic valid; vpn_t vpn; ppn_t ppn; flags_t flags;} test_entry_t;
    test_entry_t [ENTRIES-1:0] preload, expected;
    logic [ENTRIES-2:0] preload_tree = '1;
    tlb #(.ENTRIES(ENTRIES)) dut (.*);
    always #5 clk = ~clk;

    task automatic check(input bit good, input string message);
        checks++;
        if (!good) begin failures++; $fatal(1, "TLB_CHECK_FAILED %s", message); end
    endtask

    task automatic install;
        force dut.entries_q = preload;
        force dut.replacement.state_q = preload_tree;
        #1;
        release dut.entries_q;
        release dut.replacement.state_q;
    endtask

    initial begin
        for (int entry = 0; entry < ENTRIES; entry++)
            preload[entry] = '{valid:1'b1, vpn:vpn_t'(20'h80000+entry),
                               ppn:ppn_t'(22'h200000+13*entry), flags:flags_t'(8'hdf)};
        repeat (2) @(negedge clk);
        reset = 0;
        for (int hole = 0; hole < ENTRIES; hole++) begin
            preload[hole].valid = 0;
            install();
            fill_vpn = vpn_t'(20'h90000+hole);
            fill_ppn = ppn_t'(22'h300000+hole);
            fill_valid = 1;
            expected = preload;
            expected[hole] = '{valid:1'b1, vpn:fill_vpn, ppn:fill_ppn, flags:fill_flags};
            #1;
            check(int'(dut.fill_index) == hole, "lowest invalid slot");
            @(posedge clk);
            #0.001;
            check(dut.entries_q === expected, "invalid-first refill contents");
            @(negedge clk);
            fill_valid = 0;
            for (int entry = 0; entry < ENTRIES; entry++) begin
                lookup_vpn = expected[entry].vpn;
                #1;
                check(lookup_hit === 1 && lookup_ppn === expected[entry].ppn && lookup_flags === expected[entry].flags, "every slot lookup");
                check(dut.match_vector === (ENTRIES'(1) << entry), "one unique match");
                @(negedge clk);
            end
            preload[hole].valid = 1;
        end
        install();
        fill_vpn = 20'ha0000;
        fill_ppn = 22'h3fffff;
        fill_valid = 1;
        expected = preload;
        expected[ENTRIES-1] = '{valid:1'b1, vpn:fill_vpn, ppn:fill_ppn, flags:fill_flags};
        #1;
        check(int'(dut.fill_index) == ENTRIES-1, "full victim");
        @(posedge clk);
        #0.001;
        check(dut.entries_q === expected, "full refill");
        @(negedge clk);
        fill_ppn = 22'h100001;
        expected[ENTRIES-1].ppn = fill_ppn;
        #1;
        check(int'(dut.fill_index) == ENTRIES-1, "existing mapping update");
        @(posedge clk);
        #0.001;
        check(dut.entries_q === expected, "no duplicate refill");
        @(negedge clk);
        flush = 1;
        @(negedge clk);
        check(dut.entries_q === '0 && dut.replacement.state_q === '0, "all-entry flush priority");
        flush = 0;
        reset = 1;
        @(negedge clk);
        check(dut.entries_q === '0, "reset priority");
        completed = 1;
        $display("TLB_PASS N=%0d checks=%0d", ENTRIES, checks);
        $finish;
    end
    initial begin #100000; $fatal(1, "TLB_WATCHDOG"); end
endmodule
`default_nettype wire
