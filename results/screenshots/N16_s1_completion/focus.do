onerror {puts REPLAY_FAILED; quit -f -code 21}
view wave -undock -width 1800 -height 820 -x 20 -y 20
delete wave *
add wave -label "clk" -radix binary "/translation_tb/dut/clk"
add wave -label "reset" -radix binary "/translation_tb/dut/reset"
add wave -label "flush" -radix binary "/translation_tb/dut/flush"
add wave -label "req_valid" -radix binary "/translation_tb/dut/req_valid"
add wave -label "resp_valid" -radix binary "/translation_tb/dut/resp_valid"
add wave -label "completed" -radix unsigned "/translation_tb/completed"
add wave -label "failures" -radix unsigned "/translation_tb/failures"
configure wave -namecolwidth 190
configure wave -valuecolwidth 100
wave zoom range 161980ns 162011ns
wave cursor time -time 162010ns 1
wave cursor active 1
puts "SAVED_RUN_TRANSCRIPT: # TRANSLATION_PASS N=16 accepted=1317 completed=1294 canceled=23 checks=2193117"
puts "SAVED_RUN_TRANSCRIPT: # RUN_COMPLETE"
view transcript -undock -width 1500 -height 600 -x 30 -y 30
puts "OBSERVED_FINISH: accepted=1317  completed=1294  canceled=23"
puts "OBSERVED_FINISH: hits=172  misses=1145  walks=1145"
puts "OBSERVED_FINISH: first_results=1298  checks=2193117"
puts "OBSERVED_FINISH: stall_cycles=14424  queue_cycles=26  walker_busy_cycles=14546"
puts "SAVED_FULL_REGRESSION: passed=True  scope=full  steps=31  expected_failures=19"
write wave "/home/sanat/projects/github_TLB-and-Hardware-Page-Table-Walker/TLB-and-Hardware-Page-Table-Walker/results/screenshots/N16_s1_completion/native.ps" -start 161980ns -end 162011ns -portrait -width 12 -height 9 -margin 0.5
puts REPLAY_READY
after 8000 {quit -f -code 0}
