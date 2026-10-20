onerror {puts REPLAY_FAILED; quit -f -code 21}
view wave -undock -width 1800 -height 820 -x 20 -y 20
delete wave *
add wave -label "clk" -radix binary "/translation_tb/dut/clk"
add wave -label "reset" -radix binary "/translation_tb/dut/reset"
add wave -label "flush" -radix binary "/translation_tb/dut/flush"
add wave -label "req_valid" -radix binary "/translation_tb/dut/req_valid"
add wave -label "req_ready" -radix binary "/translation_tb/dut/req_ready"
add wave -label "req_va" -radix hexadecimal "/translation_tb/dut/req_va"
add wave -label "req_cookie" -radix unsigned "/translation_tb/dut/req_cookie"
add wave -label "lookup_hit" -radix binary "/translation_tb/dut/lookup_hit"
add wave -label "va_q" -radix hexadecimal "/translation_tb/dut/walker/va_q"
add wave -label "walker_state" -radix symbolic "/translation_tb/dut/walker/state_q"
add wave -label "level_q" -radix unsigned "/translation_tb/dut/walker/level_q"
add wave -label "mem_req_valid" -radix binary "/translation_tb/dut/mem_req_valid"
add wave -label "mem_req_ready" -radix binary "/translation_tb/dut/mem_req_ready"
add wave -label "mem_req_addr" -radix hexadecimal "/translation_tb/dut/mem_req_addr"
add wave -label "mem_resp_valid" -radix binary "/translation_tb/dut/mem_resp_valid"
add wave -label "mem_resp_cookie" -radix unsigned "/translation_tb/dut/mem_resp_cookie"
add wave -label "mem_resp_data" -radix hexadecimal "/translation_tb/dut/mem_resp_data"
add wave -label "fill_valid" -radix binary "/translation_tb/dut/fill_valid"
add wave -label "resp_valid" -radix binary "/translation_tb/dut/resp_valid"
add wave -label "resp_ready" -radix binary "/translation_tb/dut/resp_ready"
add wave -label "resp_cookie" -radix unsigned "/translation_tb/dut/resp_cookie"
add wave -label "resp_pa" -radix hexadecimal "/translation_tb/dut/resp_pa"
add wave -label "resp_fault" -radix symbolic "/translation_tb/dut/resp_fault"
configure wave -namecolwidth 190
configure wave -valuecolwidth 100
wave zoom range 20ns 185ns
wave cursor time -time 34.999ns 1
wave cursor active 1
write wave "/home/sanat/projects/github_TLB-and-Hardware-Page-Table-Walker/TLB-and-Hardware-Page-Table-Walker/results/screenshots/N16_s1_cold/native.ps" -start 20ns -end 185ns -portrait -width 12 -height 9 -margin 0.5
puts REPLAY_READY
after 8000 {quit -f -code 0}
