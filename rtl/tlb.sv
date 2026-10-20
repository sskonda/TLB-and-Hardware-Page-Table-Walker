`default_nettype none
module tlb #(
    parameter int unsigned ENTRIES = 4
) (
    input wire logic clk, reset, flush,
    input wire vm_pkg::vpn_t lookup_vpn,
    input wire logic lookup_touch,
    output logic lookup_hit,
    output vm_pkg::ppn_t lookup_ppn,
    output vm_pkg::flags_t lookup_flags,
    input wire logic fill_valid,
    input wire vm_pkg::vpn_t fill_vpn,
    input wire vm_pkg::ppn_t fill_ppn,
    input wire vm_pkg::flags_t fill_flags
);
    import vm_pkg::*;
    typedef logic [$clog2(ENTRIES)-1:0] index_t;
    typedef struct packed {logic valid; vpn_t vpn; ppn_t ppn; flags_t flags;} entry_t;
    entry_t entries_q [ENTRIES];
    logic [ENTRIES-1:0] match_vector;
    index_t hit_index, fill_index, victim;
    logic hit_found, fill_found, invalid_found;
    logic plru_touch;
    index_t plru_index;

    tree_plru #(.ENTRIES(ENTRIES)) replacement (
        .clk(clk), .reset(reset), .flush(flush), .touch(plru_touch),
        .touch_index(plru_index), .victim(victim)
    );
    assign plru_touch = lookup_touch || fill_valid;
    assign plru_index = fill_valid ? fill_index : hit_index;

    always_comb begin
        hit_index = '0;
        hit_found = 1'b0;
        lookup_ppn = '0;
        lookup_flags = '0;
        for (int unsigned i = 0; i < ENTRIES; i++) begin
            match_vector[i] = entries_q[i].valid && entries_q[i].vpn == lookup_vpn;
            if (match_vector[i] && !hit_found) begin
                hit_index = index_t'(i);
                hit_found = 1'b1;
                lookup_ppn = entries_q[i].ppn;
                lookup_flags = entries_q[i].flags;
            end
        end
        lookup_hit = |match_vector;
        fill_index = victim;
        fill_found = 1'b0;
        invalid_found = 1'b0;
        for (int unsigned i = 0; i < ENTRIES; i++) begin
            if (entries_q[i].valid && entries_q[i].vpn == fill_vpn && !fill_found) begin
                fill_index = index_t'(i);
                fill_found = 1'b1;
            end
        end
        for (int unsigned i = 0; i < ENTRIES; i++) begin
            if (!entries_q[i].valid && !fill_found && !invalid_found) begin
                fill_index = index_t'(i);
                invalid_found = 1'b1;
            end
        end
    end

    always_ff @(posedge clk) begin
        if (reset || flush) begin
            for (int unsigned i = 0; i < ENTRIES; i++) entries_q[i] <= '0;
        end else if (fill_valid) begin
            entries_q[fill_index] <= '{valid:1'b1, vpn:fill_vpn, ppn:fill_ppn, flags:fill_flags};
        end
    end
endmodule
`default_nettype wire
