`default_nettype none
module page_table_walker (
    input wire logic clk, reset, flush,
    input wire logic start_valid,
    output logic start_ready,
    input wire vm_pkg::va_t start_va,
    input wire vm_pkg::access_t start_access,
    input wire vm_pkg::ppn_t start_root,
    input wire vm_pkg::cookie_t start_cookie,
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
    input wire vm_pkg::cookie_t mem_resp_cookie,
    output logic fill_valid,
    output vm_pkg::vpn_t fill_vpn,
    output vm_pkg::ppn_t fill_ppn,
    output vm_pkg::flags_t fill_flags
);
    import vm_pkg::*;
    typedef enum logic [1:0] {IDLE, ISSUE, WAIT_PTE, RESULT} state_t;
    state_t state_q, state_d;
    va_t va_q, va_d;
    access_t access_q, access_d;
    cookie_t cookie_q, cookie_d;
    ppn_t table_q, table_d;
    logic level_q, level_d;
    pa_t pa_q, pa_d;
    fault_t fault_q, fault_d, decoded_fault;
    logic [INDEX_BITS-1:0] index;

    assign start_ready = state_q == IDLE && !reset && !flush;
    assign resp_valid = state_q == RESULT && !reset && !flush;
    assign resp_pa = pa_q;
    assign resp_fault = fault_q;
    assign resp_level = level_q;
    assign resp_cookie = cookie_q;
    assign index = level_q ? va_q[VA_BITS-1 -: INDEX_BITS] : va_q[OFFSET_BITS +: INDEX_BITS];
    assign mem_req_valid = state_q == ISSUE && !reset && !flush;
    assign mem_req_addr = {table_q, index, {PTE_BYTE_SHIFT{1'b0}}};
    assign mem_req_cookie = cookie_q;
    assign mem_resp_ready = 1'b1;
    assign decoded_fault = mem_resp_error ? MEMORY_ACCESS : pte_fault(mem_resp_data, level_q, access_q);
    assign fill_vpn = va_q[VA_BITS-1:OFFSET_BITS];
    assign fill_ppn = mem_resp_data[PTE_BITS-1:PTE_PPN_LSB];
    assign fill_flags = flags_t'(mem_resp_data[$bits(flags_t)-1:0]);

    always_comb begin
        state_d = state_q;
        va_d = va_q;
        access_d = access_q;
        cookie_d = cookie_q;
        table_d = table_q;
        level_d = level_q;
        pa_d = pa_q;
        fault_d = fault_q;
        fill_valid = 1'b0;
        case (state_q)
            IDLE: if (start_valid) begin
                va_d = start_va;
                access_d = start_access;
                cookie_d = start_cookie;
                table_d = start_root;
                level_d = 1'b1;
                pa_d = '0;
                fault_d = NONE;
                state_d = ISSUE;
            end
            ISSUE: if (mem_req_ready) state_d = WAIT_PTE;
            WAIT_PTE: if (mem_resp_valid && mem_resp_cookie == cookie_q) begin
                if (decoded_fault != NONE) begin
                    fault_d = decoded_fault;
                    pa_d = '0;
                    state_d = RESULT;
                end else if (level_q) begin
                    table_d = mem_resp_data[PTE_BITS-1:PTE_PPN_LSB];
                    level_d = 1'b0;
                    state_d = ISSUE;
                end else begin
                    pa_d = {mem_resp_data[PTE_BITS-1:PTE_PPN_LSB], va_q[OFFSET_BITS-1:0]};
                    fill_valid = !reset && !flush;
                    state_d = RESULT;
                end
            end
            RESULT: if (resp_ready) state_d = IDLE;
            default: state_d = IDLE;
        endcase
    end

    always_ff @(posedge clk) begin
        if (reset || flush) begin
            state_q <= IDLE;
            va_q <= '0;
            access_q <= LOAD;
            cookie_q <= '0;
            table_q <= '0;
            level_q <= 1'b1;
            pa_q <= '0;
            fault_q <= NONE;
        end else begin
            state_q <= state_d;
            va_q <= va_d;
            access_q <= access_d;
            cookie_q <= cookie_d;
            table_q <= table_d;
            level_q <= level_d;
            pa_q <= pa_d;
            fault_q <= fault_d;
        end
    end
endmodule
`default_nettype wire
