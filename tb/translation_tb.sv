`timescale 1ns/1ps
`default_nettype none
module translation_tb;
    import vm_pkg::*;
    parameter int unsigned ENTRIES = 4;
    logic clk = 0, reset = 1, flush = 0;
    logic req_valid = 0, req_ready, resp_valid, resp_ready = 1;
    va_t req_va = '0;
    access_t req_access = LOAD;
    ppn_t req_root = 1;
    cookie_t req_cookie = 0, resp_cookie;
    pa_t resp_pa;
    fault_t resp_fault;
    logic resp_level;
    logic mem_req_valid, mem_req_ready = 0, mem_resp_valid = 0, mem_resp_ready;
    pa_t mem_req_addr;
    cookie_t mem_req_cookie, mem_resp_cookie = 0;
    pte_t mem_resp_data = 0;
    logic mem_resp_error = 0;
    bit completed = 0;
    int unsigned failures = 0, cycles = 0, accepted = 0, consumed = 0, canceled = 0;
    int unsigned hits = 0, misses = 0, walks = 0, first_count = 0, checks = 0;
    int unsigned epoch = 0, sequence_number = 0, next_cookie = 1;
    int unsigned seed = 1, latency = 5, watchdog = 2000000;
    string image_path, trace_path = "", log_path, run_id = "translation", inject = "";
    integer log_file, image_file, trace_file, scan;
    byte unsigned memory [longint unsigned];
    byte unsigned reference_memory [longint unsigned];
    longint unsigned load_address;
    int unsigned load_byte;
    bit variable_latency = 0, allow_memory = 1;
    int unsigned memory_rng = 1;
    bit memory_pending = 0;
    longint unsigned memory_due;
    pa_t memory_address;
    pte_t memory_data;
    cookie_t memory_cookie;
    bit memory_error = 0;
    bit active = 0, first_seen = 0, previous_reset = 0;
    va_t active_va;
    access_t active_access;
    cookie_t active_cookie;
    longint unsigned accept_cycle, first_cycle, latency_sum = 0, consumption_sum = 0;
    pa_t expected_pa;
    int expected_fault, expected_level, expected_reads, read_index;
    pa_t expected_path [2];
    pte_t expected_words [2];
    int expected_step_fault [2];
    bit read_pending = 0;
    pa_t read_address;
    cookie_t read_cookie;
    longint unsigned read_cycle, last_read_cycle;
    int unsigned read_sequence = 0;
    int signed consumed_cookie = -1;
    bit model_valid [ENTRIES];
    vpn_t model_vpn [ENTRIES];
    ppn_t model_ppn [ENTRIES];
    byte unsigned model_flags [ENTRIES];
    logic [ENTRIES-2:0] model_tree = '0;
    int unsigned entry_fill [ENTRIES], entry_hit [ENTRIES], entry_victim [ENTRIES];
    int unsigned fault_coverage [2][10];
    int unsigned reset_count = 0, flush_count = 0, discard_count = 0;
    int model_hit_index, model_fill_index;
    bit expected_fill;

    translation_unit #(.ENTRIES(ENTRIES)) dut (.*);
    always #5 clk = ~clk;

    function automatic pte_t memory_word(input longint unsigned address);
        pte_t value;
        value = 0;
        for (int byte_index = 0; byte_index < 4; byte_index++)
            if (memory.exists(address+byte_index)) value |= pte_t'(memory[address+byte_index]) << (8*byte_index);
        return value;
    endfunction

    function automatic longint unsigned reference_word(input longint unsigned address);
        longint unsigned value;
        value = 0;
        for (int byte_index = 3; byte_index >= 0; byte_index--)
            value = value*256 + (reference_memory.exists(address+byte_index) ? reference_memory[address+byte_index] : 0);
        return value;
    endfunction

    function automatic int reference_permission(input longint unsigned flags, input int access_kind);
        if ((flags & 16) == 0) return 6;
        if ((access_kind == 0 && (flags & 2) == 0) ||
            (access_kind == 1 && (flags & 6) != 6) ||
            (access_kind == 2 && (flags & 8) == 0)) return 7;
        if ((flags & 64) == 0) return 8;
        if (access_kind == 1 && (flags & 128) == 0) return 9;
        return 0;
    endfunction

    function automatic int reference_decode(input longint unsigned word, input int level, input int access_kind);
        int rwx;
        rwx = int'((word/2)%8);
        if ((word%2) == 0 || rwx == 2 || rwx == 6) return 2;
        if (rwx == 0) begin
            if ((word & 208) != 0) return 3;
            if (level == 0) return 4;
            return 0;
        end
        if (level == 1) return 5;
        return reference_permission(word%256, access_kind);
    endfunction

    function automatic logic [ENTRIES-2:0] tree_update(input logic [ENTRIES-2:0] tree, input int leaf);
        int depth, width, first;
        tree_update = tree;
        for (int node = 0; node < ENTRIES-1; node++) begin
            depth = $clog2(node+2)-1;
            width = ENTRIES >> depth;
            first = (node+1-(1 << depth))*width;
            if (leaf >= first && leaf < first+width) tree_update[node] = leaf < first+width/2;
        end
    endfunction

    function automatic int tree_victim(input logic [ENTRIES-2:0] tree);
        bit [ENTRIES-1:0] leaves;
        int depth, width, first, discarded;
        leaves = '1;
        for (int node = 0; node < ENTRIES-1; node++) begin
            depth = $clog2(node+2)-1;
            width = ENTRIES >> depth;
            first = (node+1-(1 << depth))*width;
            discarded = first + (tree[node] ? 0 : width/2);
            for (int leaf = discarded; leaf < discarded+width/2; leaf++) leaves[leaf] = 0;
        end
        tree_victim = -1;
        for (int leaf = 0; leaf < ENTRIES; leaf++) if (leaves[leaf]) tree_victim = leaf;
    endfunction

    task automatic event_line(input string event_name, input cookie_t cookie, input string fields);
        $fdisplay(log_file, "{\"schema\":1,\"run\":\"%s\",\"seq\":%0d,\"cycle\":%0d,\"epoch\":%0d,\"txn\":%0d,\"event\":\"%s\"%s}",
                  run_id, sequence_number, cycles, epoch, cookie, event_name, fields);
        sequence_number++;
    endtask

    task automatic check(input bit good, input string message);
        checks++;
        if (!good) begin
            failures++;
            event_line("check_failed", active_cookie, $sformatf(",\"message\":\"%s\"", message));
            $fatal(1, "TRANSLATION_CHECK_FAILED %s N=%0d cycle=%0d txn=%0d", message, ENTRIES, cycles, active_cookie);
        end
    endtask

    task automatic predict_walk;
        longint unsigned address, word;
        expected_pa = 0;
        expected_fault = 0;
        expected_level = 1;
        expected_reads = 0;
        address = longint'(req_root)*4096 + (longint'(req_va)/4194304)*4;
        for (int level = 1; level >= 0; level--) begin
            word = reference_word(address);
            expected_path[1-level] = pa_t'(address);
            expected_words[1-level] = pte_t'(word);
            expected_step_fault[1-level] = reference_decode(word, level, int'(req_access));
            expected_fault = expected_step_fault[1-level];
            expected_level = level;
            expected_reads++;
            if (expected_fault != 0) break;
            if (level == 0) expected_pa = pa_t'((word/1024)*4096 + longint'(req_va)%4096);
            else address = (word/1024)*4096 + ((longint'(req_va)/4096)%1024)*4;
        end
    endtask

    always @(negedge clk) begin
        #0.001;
        mem_resp_valid = memory_pending && cycles >= memory_due;
        mem_resp_data = memory_data;
        mem_resp_cookie = memory_cookie;
        mem_resp_error = memory_error;
        mem_req_ready = allow_memory && (!memory_pending || (mem_resp_valid && mem_resp_ready));
    end

    always @(posedge clk) begin : responder
        if (mem_resp_valid && mem_resp_ready) memory_pending <= 0;
        if (mem_req_valid && mem_req_ready) begin
            memory_pending <= 1;
            memory_address <= mem_req_addr;
            memory_cookie <= mem_req_cookie;
            memory_data <= memory_word(longint'(mem_req_addr));
            memory_error <= 0;
            memory_rng = memory_rng ^ (memory_rng << 13);
            memory_rng = memory_rng ^ (memory_rng >> 17);
            memory_rng = memory_rng ^ (memory_rng << 5);
            memory_due <= cycles + (variable_latency ? 1+memory_rng%11 : latency);
        end
    end

    always @(posedge clk) begin : passive_monitor
        if (cycles >= watchdog) $fatal(1, "TRANSLATION_WATCHDOG");
        expected_fill = 0;
        if (reset || flush) begin
            if (reset && !previous_reset) begin epoch++; reset_count++; end
            if (flush) flush_count++;
            event_line(reset ? "reset" : "flush", 0, "");
            if (active) begin
                event_line("cancel", active_cookie, $sformatf(",\"first_seen\":%0d", first_seen));
                canceled++;
                active = 0;
            end
            for (int entry = 0; entry < ENTRIES; entry++) model_valid[entry] = 0;
            model_tree = '0;
            check(req_ready === 0 && resp_valid === 0 && mem_req_valid === 0, "control priority");
        end else begin
            check((^{req_ready,resp_valid,mem_req_valid,mem_resp_ready}) !== 1'bx, "known control outputs");
            if (req_valid && req_ready) begin
                check(!active, "one outstanding translation");
                check((^{req_va,req_access,req_root,req_cookie}) !== 1'bx && int'(req_access) < 3, "known request");
                active = 1;
                first_seen = 0;
                active_va = req_va;
                active_access = req_access;
                active_cookie = req_cookie;
                accept_cycle = cycles;
                read_index = 0;
                accepted++;
                model_hit_index = -1;
                for (int entry = 0; entry < ENTRIES; entry++)
                    if (model_valid[entry] && model_vpn[entry] == req_va[31:12]) begin
                        check(model_hit_index == -1, "model unique tag");
                        model_hit_index = entry;
                    end
                check(dut.lookup_hit === (model_hit_index >= 0), "lookup classification");
                if (model_hit_index >= 0) begin
                    hits++;
                    entry_hit[model_hit_index]++;
                    expected_fault = reference_permission(model_flags[model_hit_index], int'(req_access));
                    expected_pa = expected_fault == 0 ? pa_t'(longint'(model_ppn[model_hit_index])*4096 + longint'(req_va)%4096) : pa_t'(0);
                    expected_level = 0;
                    expected_reads = 0;
                    check(int'(dut.cache.hit_index) == model_hit_index, "hit entry");
                    model_tree = tree_update(model_tree, model_hit_index);
                end else begin misses++; walks++; predict_walk(); end
                event_line("accept", req_cookie, $sformatf(",\"va\":\"%08h\",\"access\":%0d,\"root\":\"%06h\",\"hit\":%0d,\"entry\":%0d,\"expected_pa\":\"%09h\",\"expected_fault\":%0d,\"expected_reads\":%0d", req_va, req_access, req_root, dut.lookup_hit, model_hit_index, expected_pa, expected_fault, expected_reads));
            end
        end
        if (mem_resp_valid && mem_resp_ready) begin
            check(read_pending, "no orphan memory response");
            check(mem_resp_cookie === read_cookie, "memory response cookie");
            check(variable_latency ? cycles-read_cycle >= 1 && cycles-read_cycle <= 11 : cycles-read_cycle == latency, "memory latency");
            event_line("pte_response", mem_resp_cookie, $sformatf(",\"read\":%0d,\"addr\":\"%09h\",\"data\":\"%08h\",\"error\":%0d", read_sequence, read_address, mem_resp_data, mem_resp_error));
            read_pending = 0;
            if (!reset && !flush && active && active_cookie == mem_resp_cookie) begin
                check(read_index < expected_reads, "expected PTE count");
                check(mem_resp_data === expected_words[read_index], "PTE response data");
                check(mem_resp_error === 0, "PTE memory error");
                check(int'(dut.walker.decoded_fault) == expected_step_fault[read_index], "PTE decode");
                event_line("decode", mem_resp_cookie, $sformatf(",\"level\":%0d,\"fault\":%0d,\"expected_fault\":%0d", 1-read_index, dut.walker.decoded_fault, expected_step_fault[read_index]));
                read_index++;
                last_read_cycle = cycles;
                if (read_index == expected_reads && expected_fault == 0) expected_fill = 1;
            end else begin discard_count++; event_line("discard", mem_resp_cookie, ""); end
        end
        if (mem_req_valid && mem_req_ready) begin
            check(active && !read_pending && read_index < expected_reads, "PTE request ownership");
            check(mem_req_cookie === active_cookie && mem_req_addr === expected_path[read_index], "PTE request path");
            read_pending = 1;
            read_address = mem_req_addr;
            read_cookie = mem_req_cookie;
            read_cycle = cycles;
            read_sequence++;
            event_line("pte_accept", mem_req_cookie, $sformatf(",\"read\":%0d,\"level\":%0d,\"addr\":\"%09h\",\"expected_addr\":\"%09h\"", read_sequence, 1-read_index, mem_req_addr, expected_path[read_index]));
        end
        check(dut.fill_valid === expected_fill, "refill enable");
        if (expected_fill) begin
            model_fill_index = -1;
            for (int entry = 0; entry < ENTRIES; entry++)
                if (!model_valid[entry] && model_fill_index == -1) model_fill_index = entry;
            if (model_fill_index == -1) model_fill_index = tree_victim(model_tree);
            check(int'(dut.cache.fill_index) == model_fill_index, "refill victim");
            event_line("refill", active_cookie, $sformatf(",\"entry\":%0d,\"expected_entry\":%0d,\"evict\":%0d,\"old_vpn\":\"%05h\",\"old_ppn\":\"%06h\",\"vpn\":\"%05h\",\"ppn\":\"%06h\",\"plru_before\":\"%h\"", dut.cache.fill_index, model_fill_index, model_valid[model_fill_index], dut.cache.entries_q[model_fill_index].vpn, dut.cache.entries_q[model_fill_index].ppn, dut.fill_vpn, dut.fill_ppn, dut.cache.replacement.state_q));
            if (model_valid[model_fill_index]) entry_victim[model_fill_index]++;
            model_valid[model_fill_index] = 1;
            model_vpn[model_fill_index] = active_va[31:12];
            model_ppn[model_fill_index] = expected_pa[33:12];
            model_flags[model_fill_index] = byte'(expected_words[expected_reads-1]);
            model_tree = tree_update(model_tree, model_fill_index);
            entry_fill[model_fill_index]++;
        end
        if (!reset && !flush && resp_valid) begin
            check(active, "no orphan translation response");
            check(resp_cookie === active_cookie && resp_pa === expected_pa && int'(resp_fault) == expected_fault && int'(resp_level) == expected_level, "translation response");
            if (!first_seen) begin
                check(expected_reads == 0 ? cycles == accept_cycle : read_index == expected_reads && cycles == last_read_cycle+1, "first result timing");
                first_seen = 1;
                first_cycle = cycles;
                first_count++;
                latency_sum += cycles-accept_cycle;
                fault_coverage[expected_level][expected_fault]++;
                event_line("first_result", active_cookie, $sformatf(",\"pa\":\"%09h\",\"fault\":%0d,\"level\":%0d,\"latency\":%0d,\"expected_pa\":\"%09h\",\"expected_fault\":%0d", resp_pa, resp_fault, resp_level, cycles-accept_cycle, expected_pa, expected_fault));
            end
            if (resp_ready) begin
                consumed++;
                consumed_cookie = int'(active_cookie);
                consumption_sum += cycles-accept_cycle;
                event_line("consume", active_cookie, $sformatf(",\"latency\":%0d,\"backpressure\":%0d", cycles-accept_cycle, cycles-first_cycle));
                active = 0;
            end
        end
        previous_reset = reset;
        #0.001;
        check(dut.cache.replacement.state_q === model_tree, "PLRU state");
        for (int entry = 0; entry < ENTRIES; entry++) begin
            check(dut.cache.entries_q[entry].valid === model_valid[entry], "entry validity");
            if (model_valid[entry]) begin
                check(dut.cache.entries_q[entry].vpn === model_vpn[entry] && dut.cache.entries_q[entry].ppn === model_ppn[entry] && dut.cache.entries_q[entry].flags === model_flags[entry], "entry mapping");
                for (int other = entry+1; other < ENTRIES; other++)
                    check(!dut.cache.entries_q[other].valid || dut.cache.entries_q[entry].vpn !== dut.cache.entries_q[other].vpn, "duplicate valid mapping");
            end
        end
        cycles++;
    end

    task automatic offer(input va_t address, input access_t kind);
        req_va = address;
        req_access = kind;
        req_cookie = cookie_t'(next_cookie++);
        req_valid = 1;
        do @(posedge clk); while (!req_ready);
        @(negedge clk);
        req_valid = 0;
        req_va = ~address;
    endtask

    task automatic transact(input va_t address, input access_t kind = LOAD, input int hold_cycles = 0);
        int target;
        target = next_cookie;
        resp_ready = hold_cycles == 0;
        offer(address, kind);
        if (hold_cycles != 0) begin
            while (!resp_valid) @(negedge clk);
            repeat (hold_cycles) @(negedge clk);
            resp_ready = 1;
        end
        while (consumed_cookie != target) @(negedge clk);
    endtask

    task automatic pulse_control(input bit use_reset);
        reset = use_reset;
        flush = !use_reset;
        @(negedge clk);
        reset = 0;
        flush = 0;
        while (memory_pending) @(negedge clk);
    endtask

    initial begin : stimulus
        int target;
        if (!$value$plusargs("IMAGE=%s", image_path)) $fatal(1, "IMAGE_REQUIRED");
        if (!$value$plusargs("LOG=%s", log_path)) $fatal(1, "LOG_REQUIRED");
        if ($value$plusargs("TRACE=%s", trace_path)) begin end
        if ($value$plusargs("SEED=%d", seed)) begin end
        if ($value$plusargs("RUNID=%s", run_id)) begin end
        if ($value$plusargs("INJECT=%s", inject)) begin end
        if ($value$plusargs("WATCHDOG=%d", watchdog)) begin end
        if ($value$plusargs("VARIABLE=%d", variable_latency)) begin end
        memory_rng = seed;
        log_file = $fopen(log_path, "w");
        check(log_file != 0, "open log");
        image_file = $fopen(image_path, "r");
        check(image_file != 0, "open image");
        while (!$feof(image_file)) begin
            scan = $fscanf(image_file, "%h %h\n", load_address, load_byte);
            check(scan == 2, "image row");
            memory[load_address] = byte'(load_byte);
            reference_memory[load_address] = byte'(load_byte);
        end
        $fclose(image_file);
        for (int entry = 0; entry < ENTRIES; entry++) begin
            entry_fill[entry] = 0;
            entry_hit[entry] = 0;
            entry_victim[entry] = 0;
        end
        for (int level = 0; level < 2; level++)
            for (int fault = 0; fault < 10; fault++) fault_coverage[level][fault] = 0;
        repeat (3) @(negedge clk);
        reset = 0;
        if (trace_path != "") begin
            trace_file = $fopen(trace_path, "r");
            check(trace_file != 0, "open trace");
            while (!$feof(trace_file)) begin
                scan = $fscanf(trace_file, "%h %d\n", load_address, load_byte);
                check(scan == 2 && load_byte < 3, "trace row");
                transact(va_t'(load_address), access_t'(load_byte));
            end
            $fclose(trace_file);
        end else begin
            transact(32'h80000031);
            transact(32'h80000fff, LOAD, 3);
            transact(32'h80000001, STORE);
            transact(32'h80000013, FETCH);
            for (int page = 1; page < ENTRIES+8; page++) transact(32'h80000000 + va_t'(page*4096+37));
            for (int page = 0; page < ENTRIES; page++) transact(32'h80000000 + va_t'(page*4096+31));
            pulse_control(0);
            for (int page = 0; page < ENTRIES; page++) transact(32'h80000000 + va_t'(page*4096+7));
            for (int phase = 0; phase < 2; phase++) begin
                pulse_control(0);
                offer(32'h80000023, LOAD);
                while (!memory_pending) @(negedge clk);
                pulse_control(phase == 0);
                transact(32'h80000023);
            end
        end
        while (active || memory_pending) @(negedge clk);
        repeat (2) @(negedge clk);
        check(accepted == consumed+canceled && hits+misses == accepted && walks == misses, "final accounting");
        event_line("finish", 0, $sformatf(",\"accepted\":%0d,\"completed\":%0d,\"canceled\":%0d,\"hits\":%0d,\"misses\":%0d,\"walks\":%0d,\"first_results\":%0d,\"latency_sum\":%0d,\"consumption_sum\":%0d,\"checks\":%0d", accepted, consumed, canceled, hits, misses, walks, first_count, latency_sum, consumption_sum, checks));
        $fclose(log_file);
        completed = 1;
        $display("TRANSLATION_PASS N=%0d accepted=%0d completed=%0d canceled=%0d checks=%0d", ENTRIES, accepted, consumed, canceled, checks);
        $finish;
    end
endmodule
`default_nettype wire
