onerror {echo RUN_SCRIPT_ERROR; quit -f -code 21}
onbreak {
    if {[examine -radix unsigned /$env(VM_TOP)/completed] == 1} {
        resume
    } else {
        echo RUN_INCOMPLETE_BREAK
        quit -f -code 22
    }
}
log -r /$env(VM_TOP)/dut/*
log /$env(VM_TOP)/clk /$env(VM_TOP)/reset /$env(VM_TOP)/flush
log /$env(VM_TOP)/completed /$env(VM_TOP)/failures
run -all
if {[examine -radix unsigned /$env(VM_TOP)/completed] != 1} {
    echo RUN_MISSING_COMPLETION
    quit -f -code 23
}
if {[examine -radix unsigned /$env(VM_TOP)/failures] != 0} {
    echo RUN_CHECKER_FAILURE
    quit -f -code 24
}
echo RUN_COMPLETE
quit -f -code 0
