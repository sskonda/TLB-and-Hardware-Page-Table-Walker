`default_nettype none
package vm_pkg;
    localparam int unsigned VA_BITS = 32;
    localparam int unsigned OFFSET_BITS = 12;
    localparam int unsigned PTE_BITS = 32;
    localparam int unsigned PTE_PPN_LSB = 10;
    localparam int unsigned PPN_BITS = PTE_BITS-PTE_PPN_LSB;
    localparam int unsigned PA_BITS = PPN_BITS+OFFSET_BITS;
    localparam int unsigned VPN_BITS = VA_BITS-OFFSET_BITS;
    localparam int unsigned LEVELS = 2;
    localparam int unsigned INDEX_BITS = VPN_BITS/LEVELS;
    localparam int unsigned PTE_BYTE_SHIFT = $clog2(PTE_BITS/8);
    localparam int unsigned COOKIE_BITS = 32;
    typedef logic [VA_BITS-1:0] va_t;
    typedef logic [PA_BITS-1:0] pa_t;
    typedef logic [VPN_BITS-1:0] vpn_t;
    typedef logic [PPN_BITS-1:0] ppn_t;
    typedef logic [PTE_BITS-1:0] pte_t;
    typedef logic [COOKIE_BITS-1:0] cookie_t;
    typedef enum logic [1:0] {LOAD, STORE, FETCH} access_t;
    typedef enum logic [3:0] {
        NONE, MEMORY_ACCESS, INVALID_PTE, NONLEAF_RESERVED, TERMINAL_POINTER,
        UNSUPPORTED_LEAF, USER_DENIED, ACCESS_DENIED, ACCESSED_CLEAR, DIRTY_CLEAR
    } fault_t;
    typedef struct packed {logic d, a, g, u, x, w, r, v;} flags_t;

    function automatic fault_t permission_fault(input flags_t flags, input access_t access);
        fault_t fault;
        fault = NONE;
        if (!flags.u) fault = USER_DENIED;
        else begin
            case (access)
                LOAD: if (!flags.r) fault = ACCESS_DENIED;
                STORE: if (!flags.r || !flags.w) fault = ACCESS_DENIED;
                FETCH: if (!flags.x) fault = ACCESS_DENIED;
                default: fault = ACCESS_DENIED;
            endcase
            if (fault == NONE && !flags.a) fault = ACCESSED_CLEAR;
            if (fault == NONE && access == STORE && !flags.d) fault = DIRTY_CLEAR;
        end
        return fault;
    endfunction

    function automatic fault_t pte_fault(input pte_t pte, input logic level, input access_t access);
        flags_t flags;
        flags = flags_t'(pte[$bits(flags_t)-1:0]);
        if (!flags.v || (flags.w && !flags.r)) return INVALID_PTE;
        if (!(flags.r || flags.w || flags.x)) begin
            if (flags.u || flags.a || flags.d) return NONLEAF_RESERVED;
            if (!level) return TERMINAL_POINTER;
            return NONE;
        end
        if (level) return UNSUPPORTED_LEAF;
        return permission_fault(flags, access);
    endfunction
endpackage
`default_nettype wire
