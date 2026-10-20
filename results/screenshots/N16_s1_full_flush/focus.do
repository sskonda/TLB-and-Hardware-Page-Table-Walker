onerror {puts REPLAY_FAILED; quit -f -code 21}
view wave -undock -width 1800 -height 820 -x 20 -y 20
delete wave *
add wave -label "clk" -radix binary "/translation_tb/dut/clk"
add wave -label "reset" -radix binary "/translation_tb/dut/reset"
add wave -label "flush" -radix binary "/translation_tb/dut/flush"
add wave -label "entries_q\[0\].valid" -radix binary "/translation_tb/dut/cache/entries_q\[0\].valid"
add wave -label "entries_q\[1\].valid" -radix binary "/translation_tb/dut/cache/entries_q\[1\].valid"
add wave -label "entries_q\[2\].valid" -radix binary "/translation_tb/dut/cache/entries_q\[2\].valid"
add wave -label "entries_q\[3\].valid" -radix binary "/translation_tb/dut/cache/entries_q\[3\].valid"
add wave -label "entries_q\[4\].valid" -radix binary "/translation_tb/dut/cache/entries_q\[4\].valid"
add wave -label "entries_q\[5\].valid" -radix binary "/translation_tb/dut/cache/entries_q\[5\].valid"
add wave -label "entries_q\[6\].valid" -radix binary "/translation_tb/dut/cache/entries_q\[6\].valid"
add wave -label "entries_q\[7\].valid" -radix binary "/translation_tb/dut/cache/entries_q\[7\].valid"
add wave -label "entries_q\[8\].valid" -radix binary "/translation_tb/dut/cache/entries_q\[8\].valid"
add wave -label "entries_q\[9\].valid" -radix binary "/translation_tb/dut/cache/entries_q\[9\].valid"
add wave -label "entries_q\[10\].valid" -radix binary "/translation_tb/dut/cache/entries_q\[10\].valid"
add wave -label "entries_q\[11\].valid" -radix binary "/translation_tb/dut/cache/entries_q\[11\].valid"
add wave -label "entries_q\[12\].valid" -radix binary "/translation_tb/dut/cache/entries_q\[12\].valid"
add wave -label "entries_q\[13\].valid" -radix binary "/translation_tb/dut/cache/entries_q\[13\].valid"
add wave -label "entries_q\[14\].valid" -radix binary "/translation_tb/dut/cache/entries_q\[14\].valid"
add wave -label "entries_q\[15\].valid" -radix binary "/translation_tb/dut/cache/entries_q\[15\].valid"
add wave -label "plru_bits" -radix hexadecimal "/translation_tb/dut/cache/replacement/state_q"
add wave -label "req_valid" -radix binary "/translation_tb/dut/req_valid"
add wave -label "req_ready" -radix binary "/translation_tb/dut/req_ready"
add wave -label "resp_valid" -radix binary "/translation_tb/dut/resp_valid"
configure wave -namecolwidth 190
configure wave -valuecolwidth 100
wave zoom range 6815ns 6870ns
wave cursor time -time 6835.001ns 1
wave cursor active 1
write wave "/home/sanat/projects/github_TLB-and-Hardware-Page-Table-Walker/TLB-and-Hardware-Page-Table-Walker/results/screenshots/N16_s1_full_flush/native.ps" -start 6815ns -end 6870ns -portrait -width 12 -height 9 -margin 0.5
puts REPLAY_READY
after 8000 {quit -f -code 0}
