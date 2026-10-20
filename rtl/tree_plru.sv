`default_nettype none
module tree_plru #(
    parameter int unsigned ENTRIES = 4
) (
    input wire logic clk,
    input wire logic reset,
    input wire logic flush,
    input wire logic touch,
    input wire logic [$clog2(ENTRIES)-1:0] touch_index,
    output logic [$clog2(ENTRIES)-1:0] victim
);
    localparam int unsigned LEVELS = $clog2(ENTRIES);
    logic [ENTRIES-2:0] state_q, state_d;
    int unsigned victim_node, touch_node;

    if (ENTRIES != 4 && ENTRIES != 8 && ENTRIES != 16) begin : invalid_capacity
        UNSUPPORTED_TLB_CAPACITY invalid_configuration();
    end

    always_comb begin
        state_d = state_q;
        victim = '0;
        victim_node = 0;
        touch_node = 0;
        for (int unsigned depth = 0; depth < LEVELS; depth++) begin
            victim[LEVELS-1-depth] = state_q[victim_node];
            victim_node = 2*victim_node + 1 + int'(state_q[victim_node]);
            if (touch) state_d[touch_node] = ~touch_index[LEVELS-1-depth];
            touch_node = 2*touch_node + 1 + int'(touch_index[LEVELS-1-depth]);
        end
    end

    always_ff @(posedge clk) begin
        if (reset || flush) state_q <= '0;
        else state_q <= state_d;
    end
endmodule
`default_nettype wire
