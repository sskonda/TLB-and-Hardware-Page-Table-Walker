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
    bit error_addresses [longint unsigned];
    longint unsigned load_address;
    int unsigned load_byte;
    bit variable_latency = 0, allow_memory = 1;
    bit empty_run = 0;
    int unsigned forced_latency = 0;
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
    cookie_t active_cookie = 0;
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
    int scenario_phase = -1, observed_phase;
    int unsigned cancellation_coverage [2][9];
    int unsigned top_states [3], walker_states [4], walker_transitions [16];
    int previous_walker = 0;
    bit response_stalled = 0, memory_stalled = 0;
    pa_t stable_pa, stable_mem_addr;
    fault_t stable_fault;
    cookie_t stable_cookie, stable_mem_cookie;
    logic stable_level;
    bit post_event;
    logic [ENTRIES-2:0] tree_before;
    int unsigned hit_matches;
    bit pte_presented = 0;
    pa_t presented_address;
    cookie_t presented_cookie;
    int read_level;
    bit interval_open [4];
    longint unsigned interval_start [4];
    cookie_t interval_cookie [4];
    bit interval_condition [4];
    longint unsigned stall_cycles = 0, queue_cycles = 0, walker_busy_cycles = 0;
    int unsigned overlap_count = 0, consecutive_hits = 0, held_request_cycles = 0;
    longint unsigned previous_accept_cycle = 0;
    bit previous_accept_hit = 0;
    int unsigned access_fault_coverage [2][10][3];
    int unsigned offer_cancel_count = 0;
    int unsigned full_flush_count = 0, full_reset_count = 0;
    bit request_stalled = 0;
    va_t stable_req_va;
    access_t stable_req_access;
    ppn_t stable_req_root;
    cookie_t stable_req_cookie;
    int top_before, walker_before;
    string before_tree_json;
    string before_valid_json;
    logic [ENTRIES-1:0] valid_before, valid_after, expected_valid;

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
        string phase;
        phase = (event_name == "state" || event_name == "fsm" || event_name == "pte_request") ? "post" :
                (event_name == "image_write" || event_name == "memory_error_clear" || event_name == "memory_error_set" || event_name == "scenario") ? "drive" : "sample";
        $fdisplay(log_file, "{\"schema\":1,\"run\":\"%s\",\"seq\":%0d,\"cycle\":%0d,\"epoch\":%0d,\"txn\":%0d,\"event\":\"%s\",\"phase\":\"%s\",\"time_ns\":%0d%s}",
                  run_id, sequence_number, cycles, epoch, cookie, event_name, phase, $time, fields);
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
            if (error_addresses.exists(address) && error_addresses[address]) expected_step_fault[1-level] = 1;
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
            memory_error <= error_addresses.exists(longint'(mem_req_addr)) && error_addresses[longint'(mem_req_addr)];
            memory_rng = memory_rng ^ (memory_rng << 13);
            memory_rng = memory_rng ^ (memory_rng >> 17);
            memory_rng = memory_rng ^ (memory_rng << 5);
            memory_due <= cycles + (forced_latency != 0 ? forced_latency : (variable_latency ? 1+memory_rng%11 : latency));
        end
    end

    always @(posedge clk) begin : passive_monitor
        if (cycles >= watchdog) $fatal(1, "TRANSLATION_WATCHDOG");
        expected_fill = 0;
        post_event = reset || flush;
        tree_before = dut.cache.replacement.state_q;
        for (int entry = 0; entry < ENTRIES; entry++) valid_before[entry] = dut.cache.entries_q[entry].valid;
        if (!reset && !flush) begin
            check((^{req_valid,resp_ready,mem_req_ready,mem_resp_valid}) !== 1'bx, "known environment control");
            if (request_stalled) check(req_valid === 1 && {req_va,req_access,req_root,req_cookie} === {stable_req_va,stable_req_access,stable_req_root,stable_req_cookie}, "held input request");
            if (response_stalled) check(resp_valid === 1 && {resp_pa,resp_fault,resp_level,resp_cookie} === {stable_pa,stable_fault,stable_level,stable_cookie}, "held translation payload");
            if (memory_stalled) check(mem_req_valid === 1 && {mem_req_addr,mem_req_cookie} === {stable_mem_addr,stable_mem_cookie}, "held memory request");
        end
        response_stalled = !reset && !flush && resp_valid && !resp_ready;
        request_stalled = !reset && !flush && req_valid && !req_ready;
        stable_req_va = req_va;
        stable_req_access = req_access;
        stable_req_root = req_root;
        stable_req_cookie = req_cookie;
        memory_stalled = !reset && !flush && mem_req_valid && !mem_req_ready;
        stable_pa = resp_pa;
        stable_fault = resp_fault;
        stable_level = resp_level;
        stable_cookie = resp_cookie;
        stable_mem_addr = mem_req_addr;
        stable_mem_cookie = mem_req_cookie;
        top_before = int'(dut.state_q);
        walker_before = int'(dut.walker.state_q);
        if (reset || flush) begin
            if (valid_before === '1) begin
                if (reset) full_reset_count++;
                else full_flush_count++;
            end
            if (reset && !previous_reset) begin epoch++; reset_count++; end
            if (flush) flush_count++;
            event_line(reset ? "reset" : "flush", 0, $sformatf(",\"reset\":%0d,\"flush\":%0d", reset, flush));
            if (active) begin
                if (scenario_phase >= 0) begin
                    if (int'(dut.state_q) == 2) observed_phase = 8;
                    else if (int'(dut.walker.state_q) == 3) observed_phase = first_seen ? 7 : 6;
                    else if (int'(dut.walker.state_q) == 1) observed_phase = dut.walker.level_q ? 0 : 3;
                    else observed_phase = dut.walker.level_q ? (mem_resp_valid ? 2 : 1) : (mem_resp_valid ? 5 : 4);
                    check(observed_phase == scenario_phase, "cancellation phase reached");
                    cancellation_coverage[reset ? 0 : 1][observed_phase]++;
                end
                event_line("cancel", active_cookie, $sformatf(",\"first_seen\":%0d", first_seen));
                canceled++;
                active = 0;
            end
            if (req_valid) begin
                offer_cancel_count++;
                event_line("offer_cancel", req_cookie, $sformatf(",\"va\":\"%08h\",\"access\":%0d,\"root\":\"%06h\"", req_va, req_access, req_root));
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
                post_event = 1;
                hit_matches = 0;
                for (int entry = 0; entry < ENTRIES; entry++) if (dut.cache.match_vector[entry]) hit_matches++;
                check((^dut.cache.match_vector) !== 1'bx && hit_matches <= 1, "multiple lookup matches");
                model_hit_index = -1;
                for (int entry = 0; entry < ENTRIES; entry++)
                    if (model_valid[entry] && model_vpn[entry] == req_va[31:12]) begin
                        check(model_hit_index == -1, "model unique tag");
                        model_hit_index = entry;
                    end
                check(dut.lookup_hit === (model_hit_index >= 0), "lookup classification");
                if (model_hit_index >= 0) begin
                    check(resp_valid === 1, "immediate hit");
                    if (previous_accept_hit && cycles == previous_accept_cycle+1) consecutive_hits++;
                    hits++;
                    entry_hit[model_hit_index]++;
                    expected_fault = reference_permission(model_flags[model_hit_index], int'(req_access));
                    expected_pa = expected_fault == 0 ? pa_t'(longint'(model_ppn[model_hit_index])*4096 + longint'(req_va)%4096) : pa_t'(0);
                    expected_level = 0;
                    expected_reads = 0;
                    check(int'(dut.cache.hit_index) == model_hit_index, "hit entry");
                    model_tree = tree_update(model_tree, model_hit_index);
                end else begin misses++; predict_walk(); end
                event_line("accept", req_cookie, $sformatf(",\"va\":\"%08h\",\"access\":%0d,\"root\":\"%06h\",\"hit\":%0d,\"entry\":%0d,\"match_vector\":\"%h\",\"expected_pa\":\"%09h\",\"expected_fault\":%0d,\"expected_reads\":%0d", req_va, req_access, req_root, dut.lookup_hit, model_hit_index, dut.cache.match_vector, expected_pa, expected_fault, expected_reads));
                previous_accept_cycle = cycles;
                previous_accept_hit = model_hit_index >= 0;
            end
        end
        if (pte_presented && (reset || flush)) begin
            event_line("pte_withdraw", presented_cookie, $sformatf(",\"addr\":\"%09h\"", presented_address));
            pte_presented = 0;
        end
        if (dut.start_walk) begin
            check(req_valid && req_ready && model_hit_index == -1, "actual walk start");
            walks++;
            event_line("walk_start", req_cookie, "");
        end
        if (mem_resp_valid && mem_resp_ready) begin
            check((^{mem_resp_cookie,mem_resp_data,mem_resp_error}) !== 1'bx, "known memory response");
            check(read_pending, "no orphan memory response");
            check(mem_resp_cookie === read_cookie, "memory response cookie");
            check(variable_latency ? cycles-read_cycle >= 1 && cycles-read_cycle <= 11 : cycles-read_cycle == latency, "memory latency");
            event_line("pte_response", mem_resp_cookie, $sformatf(",\"read\":%0d,\"level\":%0d,\"addr\":\"%09h\",\"data\":\"%08h\",\"error\":%0d,\"expected_data\":\"%08h\",\"elapsed\":%0d", read_sequence, read_level, read_address, mem_resp_data, mem_resp_error, reference_word(longint'(read_address)), cycles-read_cycle));
            read_pending = 0;
            if (!reset && !flush && active && active_cookie == mem_resp_cookie) begin
                check(read_index < expected_reads, "expected PTE count");
                check(mem_resp_data === expected_words[read_index], "PTE response data");
                check(mem_resp_error === (expected_step_fault[read_index] == 1), "PTE memory error");
                check(int'(dut.walker.decoded_fault) == expected_step_fault[read_index], "PTE decode");
                event_line("decode", mem_resp_cookie, $sformatf(",\"level\":%0d,\"fault\":%0d,\"expected_fault\":%0d", 1-read_index, dut.walker.decoded_fault, expected_step_fault[read_index]));
                read_index++;
                last_read_cycle = cycles;
                if (read_index == expected_reads && expected_fault == 0) expected_fill = 1;
            end else begin
                discard_count++;
                if (active && mem_req_valid && mem_req_ready) overlap_count++;
                event_line("discard", mem_resp_cookie, "");
            end
        end
        if (mem_req_valid && mem_req_ready) begin
            check(active && !read_pending && read_index < expected_reads, "PTE request ownership");
            check(mem_req_cookie === active_cookie && mem_req_addr === expected_path[read_index], "PTE request path");
            read_pending = 1;
            read_address = mem_req_addr;
            read_cookie = mem_req_cookie;
            read_cycle = cycles;
            read_level = 1-read_index;
            read_sequence++;
            pte_presented = 0;
            event_line("pte_accept", mem_req_cookie, $sformatf(",\"read\":%0d,\"level\":%0d,\"addr\":\"%09h\",\"expected_addr\":\"%09h\"", read_sequence, 1-read_index, mem_req_addr, expected_path[read_index]));
        end
        check(dut.fill_valid === expected_fill, "refill enable");
        if (expected_fill) begin
            post_event = 1;
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
            check((^{resp_cookie,resp_pa,resp_fault,resp_level}) !== 1'bx, "known translation payload");
            check(resp_cookie === active_cookie && resp_pa === expected_pa && int'(resp_fault) == expected_fault && int'(resp_level) == expected_level, "translation response");
            if (!first_seen) begin
                check(expected_reads == 0 ? cycles == accept_cycle : read_index == expected_reads && cycles == last_read_cycle+1, "first result timing");
                first_seen = 1;
                first_cycle = cycles;
                first_count++;
                latency_sum += cycles-accept_cycle;
                fault_coverage[expected_level][expected_fault]++;
                access_fault_coverage[expected_level][expected_fault][int'(active_access)]++;
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
        interval_condition[0] = req_valid && !req_ready && !reset && !flush;
        interval_condition[1] = mem_req_valid && !mem_req_ready;
        interval_condition[2] = resp_valid && !resp_ready;
        interval_condition[3] = active && !first_seen;
        if (interval_condition[0]) begin queue_cycles++; held_request_cycles++; end
        if (interval_condition[3]) stall_cycles++;
        if (int'(dut.walker.state_q) != 0) walker_busy_cycles++;
        for (int channel = 0; channel < 4; channel++) begin
            if (interval_condition[channel] && !interval_open[channel]) begin
                interval_open[channel] = 1;
                interval_start[channel] = cycles;
                interval_cookie[channel] = channel == 0 ? req_cookie : active_cookie;
            end else if (!interval_condition[channel] && interval_open[channel]) begin
                event_line("stall_interval", interval_cookie[channel], $sformatf(",\"channel\":%0d,\"start\":%0d,\"end\":%0d,\"length\":%0d", channel, interval_start[channel], cycles, cycles-interval_start[channel]));
                interval_open[channel] = 0;
            end
        end
        #0.001;
        check(dut.cache.replacement.state_q === model_tree, "PLRU state");
        for (int entry = 0; entry < ENTRIES; entry++) begin
            valid_after[entry] = dut.cache.entries_q[entry].valid;
            expected_valid[entry] = model_valid[entry];
            check(dut.cache.entries_q[entry].valid === model_valid[entry], "entry validity");
            if (model_valid[entry]) begin
                check(dut.cache.entries_q[entry].vpn === model_vpn[entry] && dut.cache.entries_q[entry].ppn === model_ppn[entry] && dut.cache.entries_q[entry].flags === model_flags[entry], "entry mapping");
                for (int other = entry+1; other < ENTRIES; other++)
                    check(!dut.cache.entries_q[other].valid || dut.cache.entries_q[entry].vpn !== dut.cache.entries_q[other].vpn, "duplicate valid mapping");
            end
        end
        before_tree_json = (^tree_before) === 1'bx ? "null" : $sformatf("\"%h\"", tree_before);
        before_valid_json = (^valid_before) === 1'bx ? "null" : $sformatf("\"%h\"", valid_before);
        if (post_event) event_line("state", active_cookie, $sformatf(",\"plru_before\":%s,\"plru_after\":\"%h\",\"expected_plru\":\"%h\",\"valid_before\":%s,\"valid_after\":\"%h\",\"expected_valid\":\"%h\"", before_tree_json, dut.cache.replacement.state_q, model_tree, before_valid_json, valid_after, expected_valid));
        check((^{dut.state_q,dut.walker.state_q}) !== 1'bx && int'(dut.state_q) < 3, "known controller state");
        if (cycles == 0 || top_before != int'(dut.state_q) || walker_before != int'(dut.walker.state_q))
            event_line("fsm", active_cookie, $sformatf(",\"top\":%0d,\"walker\":%0d", dut.state_q, dut.walker.state_q));
        if (mem_req_valid && !pte_presented) begin
            check(active && mem_req_cookie === active_cookie && read_index < expected_reads && mem_req_addr === expected_path[read_index] && int'(dut.walker.level_q) == 1-read_index, "PTE presentation path");
            pte_presented = 1;
            presented_address = mem_req_addr;
            presented_cookie = mem_req_cookie;
            event_line("pte_request", mem_req_cookie, $sformatf(",\"level\":%0d,\"addr\":\"%09h\",\"expected_addr\":\"%09h\"", dut.walker.level_q, mem_req_addr, expected_path[read_index]));
        end
        top_states[int'(dut.state_q)]++;
        walker_states[int'(dut.walker.state_q)]++;
        walker_transitions[previous_walker*4+int'(dut.walker.state_q)]++;
        previous_walker = int'(dut.walker.state_q);
        cycles++;
    end

    task automatic set_word(input longint unsigned address, input pte_t value);
        for (int byte_index = 0; byte_index < 4; byte_index++) begin
            memory[address+byte_index] = byte'(value >> (byte_index*8));
            reference_memory[address+byte_index] = byte'(value >> (byte_index*8));
        end
        event_line("image_write", 0, $sformatf(",\"addr\":\"%09h\",\"data\":\"%08h\"", address, value));
    endtask

    task automatic restore_base;
        set_word(64'h1800, 32'h00000801);
        set_word(64'h2000, 32'h80004cdf);
        error_addresses.delete();
        event_line("memory_error_clear", 0, "");
    endtask

    task automatic malformed(input int level, input pte_t value, input access_t kind);
        pulse_control(0);
        restore_base();
        set_word(level == 1 ? 64'h1800 : 64'h2000, value);
        transact(32'h800000b7, kind);
    endtask

    task automatic cancel_phase(input int phase, input bit use_reset);
        pulse_control(0);
        restore_base();
        forced_latency = latency;
        if (phase == 8) transact(32'h80000023);
        allow_memory = phase != 0;
        resp_ready = phase < 6;
        scenario_phase = phase;
        event_line("scenario", 0, $sformatf(",\"name\":\"cancellation\",\"control\":%0d,\"cancel_phase\":%0d,\"memory_latency\":%0d", use_reset ? 0 : 1, phase, forced_latency));
        offer(32'h80000023, LOAD);
        case (phase)
            0: repeat (3) @(negedge clk);
            1: while (!(memory_pending && read_index == 0)) @(negedge clk);
            2: while (!(memory_pending && read_index == 0 && cycles == memory_due)) @(negedge clk);
            3: while (!(read_index == 1 && !memory_pending)) @(negedge clk);
            4: while (!(memory_pending && read_index == 1)) @(negedge clk);
            5: while (!(memory_pending && read_index == 1 && cycles == memory_due)) @(negedge clk);
            6: begin while (!resp_valid) @(negedge clk); resp_ready = 1; end
            7: begin while (!resp_valid) @(negedge clk); repeat (2) @(negedge clk); end
            8: begin end
        endcase
        allow_memory = 1;
        pulse_control(use_reset);
        scenario_phase = -1;
        resp_ready = 1;
        transact(32'h80000091);
        forced_latency = 0;
    endtask

    task automatic overlap_cancel(input bit use_reset);
        int target;
        pulse_control(0);
        restore_base();
        forced_latency = latency;
        offer(32'h80000017, LOAD);
        while (!memory_pending) @(negedge clk);
        reset = use_reset;
        flush = !use_reset;
        @(negedge clk);
        reset = 0;
        flush = 0;
        target = next_cookie;
        offer(32'h80001093, LOAD);
        while (consumed_cookie != target) @(negedge clk);
        forced_latency = 0;
    endtask

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
        int unsigned traffic_rng;
        pte_t bad_values [10];
        if (!$value$plusargs("IMAGE=%s", image_path)) $fatal(1, "IMAGE_REQUIRED");
        if (!$value$plusargs("LOG=%s", log_path)) $fatal(1, "LOG_REQUIRED");
        if ($value$plusargs("TRACE=%s", trace_path)) begin end
        if ($value$plusargs("SEED=%d", seed)) begin end
        if ($value$plusargs("RUNID=%s", run_id)) begin end
        if ($value$plusargs("INJECT=%s", inject)) begin end
        if ($value$plusargs("WATCHDOG=%d", watchdog)) begin end
        if ($value$plusargs("VARIABLE=%d", variable_latency)) begin end
        if ($value$plusargs("EMPTY=%d", empty_run)) begin end
        memory_rng = seed;
        log_file = $fopen(log_path, "w");
        check(log_file != 0, "open log");
        image_file = $fopen(image_path, "r");
        check(image_file != 0, "open image");
        while (!$feof(image_file)) begin
            scan = $fscanf(image_file, "%h %h\n", load_address, load_byte);
            check(scan == 2 && (^{load_address,load_byte}) !== 1'bx && load_address < 64'h400000000 && load_byte < 256 && !memory.exists(load_address), "image row");
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
        for (int level = 0; level < 2; level++)
            for (int fault = 0; fault < 10; fault++)
                for (int kind = 0; kind < 3; kind++) access_fault_coverage[level][fault][kind] = 0;
        for (int channel = 0; channel < 4; channel++) interval_open[channel] = 0;
        for (int control = 0; control < 2; control++)
            for (int phase = 0; phase < 9; phase++) cancellation_coverage[control][phase] = 0;
        for (int state_number = 0; state_number < 3; state_number++) top_states[state_number] = 0;
        for (int state_number = 0; state_number < 4; state_number++) walker_states[state_number] = 0;
        for (int transition = 0; transition < 16; transition++) walker_transitions[transition] = 0;
        repeat (3) @(negedge clk);
        reset = 0;
        if (inject == "timeout") forever @(negedge clk);
        if (inject == "unexpected") $stop;
        if (inject == "finishbad") begin completed = 1; $stop; end
        if (inject == "checker") force dut.resp_pa = 34'h1;
        if (inject == "unknown") force dut.resp_pa = 'x;
        if (inject == "cookie") force dut.resp_cookie = 32'hffffffff;
        if (inject == "path") force dut.mem_req_addr = 34'h1804;
        if (inject == "duplicate") begin
            transact(32'h80000017);
            force dut.cache.entries_q[1] = {1'b1, 20'h80000, 22'h200013, 8'hdf};
        end
        if (inject == "victim" || inject == "flush") begin
            for (int page = 0; page < ENTRIES; page++) transact(32'h80000000 + va_t'(page*4096));
            if (inject == "victim") force dut.cache.fill_index = $clog2(ENTRIES)'(ENTRIES-1);
            else begin
                force dut.cache.entries_q[ENTRIES-1].valid = 1'b1;
                pulse_control(0);
            end
        end
        if (empty_run) begin end
        else if (trace_path != "") begin
            trace_file = $fopen(trace_path, "r");
            check(trace_file != 0, "open trace");
            while (!$feof(trace_file)) begin
                scan = $fscanf(trace_file, "%h %d\n", load_address, load_byte);
                check(scan == 2 && (^{load_address,load_byte}) !== 1'bx && load_address < 64'h100000000 && load_byte < 3, "trace row");
                transact(va_t'(load_address), access_t'(load_byte));
            end
            $fclose(trace_file);
        end else begin
            transact(32'h80000031);
            transact(32'h80000fff, LOAD, 3);
            transact(32'h80000001, STORE);
            transact(32'h80000013, FETCH);
            if (inject == "victim") transact(32'h80070013);
            for (int delay_value = 1; delay_value <= 7; delay_value += delay_value == 1 ? 1 : 5) begin
                transact(32'h80000031, LOAD, delay_value);
                pulse_control(0);
                allow_memory = 0;
                target = next_cookie;
                offer(32'h80000071, LOAD);
                repeat (delay_value) @(negedge clk);
                allow_memory = 1;
                while (consumed_cookie != target) @(negedge clk);
                pulse_control(0);
                transact(32'h80000031, LOAD, delay_value);
            end
            for (int page = 1; page < ENTRIES+8; page++) transact(32'h80000000 + va_t'(page*4096+37));
            for (int page = 0; page < ENTRIES; page++) transact(32'h80000000 + va_t'(page*4096+31));
            pulse_control(0);
            for (int page = 0; page < ENTRIES; page++) transact(32'h80000000 + va_t'(page*4096+7));
            for (int page = 0; page < ENTRIES; page++) transact(32'h80000000 + va_t'(page*4096+109));
            pulse_control(0);
            for (int page = 0; page < ENTRIES; page++) transact(32'h80000000 + va_t'(page*4096+113));
            pulse_control(1);
            for (int page = 0; page < ENTRIES; page++) transact(32'h80000000 + va_t'(page*4096+117));
            pulse_control(0);
            offer(32'h80000051, LOAD);
            offer(32'h80001051, LOAD);
            transact(32'h80002051);
            for (int phase = 0; phase < 2; phase++) begin
                pulse_control(0);
                offer(32'h80000023, LOAD);
                while (!memory_pending) @(negedge clk);
                pulse_control(phase == 0);
                transact(32'h80000023);
            end
            bad_values[0] = 32'h80004cde;
            bad_values[1] = 32'h80004cd5;
            bad_values[2] = 32'h80004cdd;
            bad_values[3] = 32'h00000811;
            bad_values[4] = 32'h00000841;
            bad_values[5] = 32'h00000881;
            bad_values[6] = 32'h00000851;
            bad_values[7] = 32'h00000891;
            bad_values[8] = 32'h000008c1;
            bad_values[9] = 32'h000008d1;
            for (int level = 0; level < 2; level++) begin
                for (int bad = 0; bad < 10; bad++)
                    for (int kind = 0; kind < 3; kind++) malformed(level, bad_values[bad], access_t'(kind));
                for (int encoding = 1; encoding < 8; encoding++)
                    for (int kind = 0; kind < 3; kind++) malformed(level, 32'h80004cd1 | pte_t'(encoding << 1), access_t'(kind));
                for (int kind = 0; kind < 3; kind++) begin
                    pulse_control(0);
                    restore_base();
                    error_addresses[level == 1 ? 64'h1800 : 64'h2000] = 1;
                    event_line("memory_error_set", 0, $sformatf(",\"addr\":\"%09h\"", level == 1 ? 64'h1800 : 64'h2000));
                    transact(32'h80000023, access_t'(kind));
                end
            end
            for (int kind = 0; kind < 3; kind++) malformed(0, 32'h00000801, access_t'(kind));
            for (int kind = 0; kind < 3; kind++) begin
                malformed(1, 32'h80004cdf, access_t'(kind));
                malformed(0, 32'h80004ccf, access_t'(kind));
                malformed(0, 32'h80004c9f, access_t'(kind));
            end
            malformed(0, 32'h80004cd9, LOAD);
            malformed(0, 32'h80004cd3, STORE);
            malformed(0, 32'h80004cd3, FETCH);
            malformed(0, 32'h80004c5f, STORE);
            malformed(0, 32'h80004c13, STORE);
            malformed(0, 32'h80004c99, LOAD);
            malformed(0, 32'h80004c1f, STORE);
            malformed(0, 32'h80004c8f, FETCH);
            pulse_control(0);
            restore_base();
            set_word(64'h2000, 32'h80004c5f);
            transact(32'h80000011, LOAD);
            transact(32'h80000019, STORE);
            set_word(64'h1000, 32'h00000c01);
            set_word(64'h3000, 32'hc00004df);
            set_word(64'h17fc, 32'h00001001);
            set_word(64'h4ffc, 32'h400004df);
            set_word(64'h1ffc, 32'h40001001);
            set_word(64'h100004ffc, 32'hffffffff);
            pulse_control(0);
            transact(32'h00000001);
            transact(32'h7fffffff);
            transact(32'h80000001);
            transact(32'hffffffff);
            transact(32'hffffffff);
            for (int control = 0; control < 2; control++)
                for (int phase = 0; phase < 9; phase++) cancel_phase(phase, control == 0);
            overlap_cancel(1);
            overlap_cancel(0);
            pulse_control(0);
            restore_base();
            set_word(64'h2000, 32'h80004cd3);
            target = next_cookie;
            offer(32'h800000c5, LOAD);
            req_access = FETCH;
            req_root = 22'h3fffff;
            while (consumed_cookie != target) @(negedge clk);
            req_root = 1;
            req_access = LOAD;
            transact(32'h800000c7, STORE);
            transact(32'h800000c9, FETCH);
            malformed(0, 32'h80004cd9, FETCH);
            transact(32'h80000093, LOAD);
            transact(32'h80000095, STORE);
            malformed(0, 32'h80004cd7, STORE);
            transact(32'h80000097, FETCH);
            malformed(0, 32'h80004cdb, LOAD);
            transact(32'h80000099, FETCH);
            transact(32'h8000009b, STORE);
            for (int control = 0; control < 2; control++) begin
                pulse_control(0);
                restore_base();
                transact(32'h800000a1);
                req_va = 32'h800000a3;
                req_access = LOAD;
                req_root = 1;
                req_cookie = cookie_t'(next_cookie++);
                req_valid = 1;
                reset = control == 0;
                flush = control == 1;
                @(negedge clk);
                req_valid = 0;
                reset = 0;
                flush = 0;
                transact(32'h800000a5);
            end
            pulse_control(0);
            restore_base();
            forced_latency = latency;
            offer(32'h800000a7, LOAD);
            while (!memory_pending) @(negedge clk);
            reset = 1;
            flush = 1;
            repeat (2) @(negedge clk);
            reset = 0;
            flush = 0;
            @(negedge clk);
            reset = 1;
            @(negedge clk);
            reset = 0;
            while (memory_pending) @(negedge clk);
            forced_latency = 0;
            transact(32'h800000a9);
            pulse_control(0);
            restore_base();
            traffic_rng = seed;
            for (int page = 0; page < 128; page++) begin
                traffic_rng ^= traffic_rng << 13;
                traffic_rng ^= traffic_rng >> 17;
                traffic_rng ^= traffic_rng << 5;
                set_word(64'h2000+longint'(page*4), ((32'h300000 | (traffic_rng & 32'hffff)) << 10) | 32'hdf);
            end
            for (int transaction = 0; transaction < 1000; transaction++) begin
                traffic_rng ^= traffic_rng << 13;
                traffic_rng ^= traffic_rng >> 17;
                traffic_rng ^= traffic_rng << 5;
                transact(32'h80000000 + va_t'((traffic_rng & 127)*4096 + ((traffic_rng >> 9) & 4095)), access_t'(traffic_rng%3), transaction%17 == 0 ? 2 : 0);
                if (transaction%31 == 0) repeat (3) @(negedge clk);
            end
            for (int entry = 0; entry < ENTRIES; entry++) begin
                check(entry_fill[entry] > 0 && entry_hit[entry] > 0 && entry_victim[entry] > 0, "entry coverage");
                event_line("entry_coverage", 0, $sformatf(",\"entry\":%0d,\"fill\":%0d,\"hit\":%0d,\"victim\":%0d", entry, entry_fill[entry], entry_hit[entry], entry_victim[entry]));
            end
            if (inject == "coverage") cancellation_coverage[0][0] = 0;
            for (int control = 0; control < 2; control++)
                for (int phase = 0; phase < 9; phase++) begin
                    check(cancellation_coverage[control][phase] > 0, "cancel coverage");
                    event_line("coverage", 0, $sformatf(",\"category\":\"cancel_%0d\",\"bin\":%0d,\"count\":%0d", control, phase, cancellation_coverage[control][phase]));
                end
            for (int state_number = 0; state_number < 3; state_number++) begin
                check(top_states[state_number] > 0, "wrapper state coverage");
                event_line("coverage", 0, $sformatf(",\"category\":\"wrapper_state\",\"bin\":%0d,\"count\":%0d", state_number, top_states[state_number]));
            end
            for (int state_number = 0; state_number < 4; state_number++) begin
                check(walker_states[state_number] > 0, "walker state coverage");
                event_line("coverage", 0, $sformatf(",\"category\":\"walker_state\",\"bin\":%0d,\"count\":%0d", state_number, walker_states[state_number]));
            end
            for (int level = 0; level < 2; level++) begin
                check(fault_coverage[level][1] > 0 && fault_coverage[level][2] > 0 && fault_coverage[level][3] > 0, "both-level fault coverage");
                for (int kind = 0; kind < 3; kind++) begin
                    for (int fault = 1; fault <= 3; fault++) check(access_fault_coverage[level][fault][kind] > 0, "fault access coverage");
                    if (level == 1) check(access_fault_coverage[1][5][kind] > 0, "unsupported leaf access coverage");
                    else begin
                        check(access_fault_coverage[0][4][kind] > 0 && access_fault_coverage[0][6][kind] > 0 && access_fault_coverage[0][7][kind] > 0 && access_fault_coverage[0][8][kind] > 0, "final-level access coverage");
                    end
                end
            end
            for (int level = 0; level < 2; level++)
                for (int fault = 0; fault < 10; fault++)
                    for (int kind = 0; kind < 3; kind++)
                        if (access_fault_coverage[level][fault][kind] > 0)
                            event_line("coverage", 0, $sformatf(",\"category\":\"fault_access\",\"bin\":%0d,\"count\":%0d", level*30+fault*3+kind, access_fault_coverage[level][fault][kind]));
            check(fault_coverage[1][5] > 0 && fault_coverage[0][4] > 0 && fault_coverage[0][6] > 0 && fault_coverage[0][7] > 0 && fault_coverage[0][8] > 0 && fault_coverage[0][9] > 0, "leaf fault coverage");
            for (int transition = 0; transition < 16; transition++) begin
                if (transition == 0 || transition == 1 || transition == 4 || transition == 5 || transition == 6 || transition == 8 || transition == 9 || transition == 10 || transition == 11 || transition == 12 || transition == 15)
                    begin
                        check(walker_transitions[transition] > 0, "walker transition coverage");
                        event_line("coverage", 0, $sformatf(",\"category\":\"walker_transition\",\"bin\":%0d,\"count\":%0d", transition, walker_transitions[transition]));
                    end
                else check(walker_transitions[transition] == 0, "illegal walker transition");
            end
            check(overlap_count >= 2 && consecutive_hits > 0 && held_request_cycles > 0 && offer_cancel_count >= 2, "traffic conflict coverage");
            check(full_flush_count > 0 && full_reset_count > 0, "populated control coverage");
            event_line("coverage", 0, $sformatf(",\"category\":\"full_control\",\"bin\":0,\"count\":%0d", full_flush_count));
            event_line("coverage", 0, $sformatf(",\"category\":\"full_control\",\"bin\":1,\"count\":%0d", full_reset_count));
        end
        while (active || memory_pending) @(negedge clk);
        repeat (2) @(negedge clk);
        check(accepted == consumed+canceled && hits+misses == accepted && walks == misses, "final accounting");
        event_line("finish", 0, $sformatf(",\"accepted\":%0d,\"completed\":%0d,\"canceled\":%0d,\"hits\":%0d,\"misses\":%0d,\"walks\":%0d,\"first_results\":%0d,\"latency_sum\":%0d,\"consumption_sum\":%0d,\"stall_cycles\":%0d,\"queue_cycles\":%0d,\"walker_busy_cycles\":%0d,\"checks\":%0d", accepted, consumed, canceled, hits, misses, walks, first_count, latency_sum, consumption_sum, stall_cycles, queue_cycles, walker_busy_cycles, checks));
        $fclose(log_file);
        completed = 1;
        $display("TRANSLATION_PASS N=%0d accepted=%0d completed=%0d canceled=%0d checks=%0d", ENTRIES, accepted, consumed, canceled, checks);
        $finish;
    end
endmodule
`default_nettype wire
