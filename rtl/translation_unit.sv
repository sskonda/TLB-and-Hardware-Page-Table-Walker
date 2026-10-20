`default_nettype none
module translation_unit #(
    parameter int unsigned ENTRIES = 4
) (
    input wire logic clk, reset, flush,
    input wire logic req_valid,
    output logic req_ready,
    input wire vm_pkg::va_t req_va,
    input wire vm_pkg::access_t req_access,
    input wire vm_pkg::ppn_t req_root,
    input wire vm_pkg::cookie_t req_cookie,
    output logic resp_valid,
    input wire logic resp_ready,
    output vm_pkg::pa_t resp_pa,
    output vm_pkg::fault_t resp_fault,
    output logic resp_level,
    output vm_pkg::cookie_t resp_cookie,
    output logic mem_req_valid,
    input wire logic mem_req_ready,
    output vm_pkg::pa_t mem_req_addr,
    output vm_pkg::cookie_t mem_req_cookie,
    input wire logic mem_resp_valid,
    output logic mem_resp_ready,
    input wire vm_pkg::pte_t mem_resp_data,
    input wire logic mem_resp_error,
    input wire vm_pkg::cookie_t mem_resp_cookie
);
    import vm_pkg::*;
    typedef enum logic [1:0] {IDLE, WALK, HOLD_HIT} state_t;
    state_t state_q, state_d;
    logic lookup_hit, lookup_touch, start_walk, walk_ready;
    ppn_t lookup_ppn;
    flags_t lookup_flags;
    logic fill_valid;
    vpn_t fill_vpn;
    ppn_t fill_ppn;
    flags_t fill_flags;
    logic walk_valid, walk_consume, walk_level;
    pa_t walk_pa, held_pa_q, held_pa_d;
    fault_t walk_fault, hit_fault, held_fault_q, held_fault_d;
    cookie_t walk_cookie, held_cookie_q, held_cookie_d;

    tlb #(.ENTRIES(ENTRIES)) cache (
        .clk(clk), .reset(reset), .flush(flush),
        .lookup_vpn(req_va[VA_BITS-1:OFFSET_BITS]), .lookup_touch(lookup_touch),
        .lookup_hit(lookup_hit), .lookup_ppn(lookup_ppn), .lookup_flags(lookup_flags),
        .fill_valid(fill_valid), .fill_vpn(fill_vpn), .fill_ppn(fill_ppn), .fill_flags(fill_flags)
    );
    page_table_walker walker (
        .clk(clk), .reset(reset), .flush(flush), .start_valid(start_walk), .start_ready(walk_ready),
        .start_va(req_va), .start_access(req_access), .start_root(req_root), .start_cookie(req_cookie),
        .resp_valid(walk_valid), .resp_ready(walk_consume), .resp_pa(walk_pa),
        .resp_fault(walk_fault), .resp_level(walk_level), .resp_cookie(walk_cookie),
        .mem_req_valid(mem_req_valid), .mem_req_ready(mem_req_ready), .mem_req_addr(mem_req_addr),
        .mem_req_cookie(mem_req_cookie), .mem_resp_valid(mem_resp_valid), .mem_resp_ready(mem_resp_ready),
        .mem_resp_data(mem_resp_data), .mem_resp_error(mem_resp_error), .mem_resp_cookie(mem_resp_cookie),
        .fill_valid(fill_valid), .fill_vpn(fill_vpn), .fill_ppn(fill_ppn), .fill_flags(fill_flags)
    );
    assign req_ready = state_q == IDLE && walk_ready && !reset && !flush;
    assign lookup_touch = req_valid && req_ready && lookup_hit;
    assign start_walk = req_valid && req_ready && !lookup_hit;
    assign hit_fault = permission_fault(lookup_flags, req_access);
    assign walk_consume = state_q == WALK && resp_ready && !reset && !flush;

    always_comb begin
        state_d = state_q;
        held_pa_d = held_pa_q;
        held_fault_d = held_fault_q;
        held_cookie_d = held_cookie_q;
        resp_valid = 1'b0;
        resp_pa = '0;
        resp_fault = NONE;
        resp_level = 1'b0;
        resp_cookie = '0;
        case (state_q)
            IDLE: begin
                if (req_valid && req_ready) begin
                    if (lookup_hit) begin
                        resp_valid = 1'b1;
                        resp_pa = hit_fault == NONE ? {lookup_ppn, req_va[OFFSET_BITS-1:0]} : pa_t'('0);
                        resp_fault = hit_fault;
                        resp_cookie = req_cookie;
                        if (!resp_ready) begin
                            held_pa_d = resp_pa;
                            held_fault_d = resp_fault;
                            held_cookie_d = resp_cookie;
                            state_d = HOLD_HIT;
                        end
                    end else state_d = WALK;
                end
            end
            WALK: begin
                resp_valid = walk_valid;
                resp_pa = walk_pa;
                resp_fault = walk_fault;
                resp_level = walk_level;
                resp_cookie = walk_cookie;
                if (walk_valid && resp_ready) state_d = IDLE;
            end
            HOLD_HIT: begin
                resp_valid = 1'b1;
                resp_pa = held_pa_q;
                resp_fault = held_fault_q;
                resp_cookie = held_cookie_q;
                if (resp_ready) state_d = IDLE;
            end
            default: state_d = IDLE;
        endcase
        if (reset || flush) resp_valid = 1'b0;
    end

    always_ff @(posedge clk) begin
        if (reset || flush) begin
            state_q <= IDLE;
            held_pa_q <= '0;
            held_fault_q <= NONE;
            held_cookie_q <= '0;
        end else begin
            state_q <= state_d;
            held_pa_q <= held_pa_d;
            held_fault_q <= held_fault_d;
            held_cookie_q <= held_cookie_d;
        end
    end
endmodule
`default_nettype wire
