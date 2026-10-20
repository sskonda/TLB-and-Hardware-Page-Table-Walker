set root [file normalize [file join [file dirname [info script]] ..]]
set sources [list [file join $root rtl tree_plru.sv] [file join $root tb plru_tb.sv]]
set library_command [expr {[info exists env(VM_VLIB)] ? $env(VM_VLIB) : [list vlib]}]
set compiler_command [expr {[info exists env(VM_VLOG)] ? $env(VM_VLOG) : [list vlog]}]
if {[catch {
    puts [exec {*}$library_command work 2>@1]
    puts [exec {*}$compiler_command -sv -work work {*}$sources 2>@1]
} reason]} {
    puts stderr "COMPILE_FAILED: $reason"
    exit 21
}
