# Windows 4-MiB streams: initial failed control run

At base `6dc2565bebe137063c218cc90fa748d24559d1a5`, test overlay SHA-256
`37c64743d9c5b5ebca2d199a5a93bf2481561c1089da41342ec0b4303215acdb`, native
Windows 11 x86_64 and Rust/Cargo 1.77.2 compiled the new test target with
`testing-environ,sys,net`. All twelve selectors exited 101 but failed before
their intended wrong assertions: text results raised `ErrorDataTooLarge("Length
of string")`; raw results raised `ErrorDataTooLarge("Size of array/BLOB")`.
The suite was not started and no acceptance follows.

The original test configured the Engine limit to 4 MiB plus 1 KiB. The
Engine's `calc_map_sizes` adds the two stream field sizes, so this limit cannot
hold a result containing two 4-MiB fields. The proposed narrow correction sets
the Engine's aggregate limits to 8 MiB plus 2 KiB; the independent per-stream
`max_output` remains 4 MiB plus 1 KiB. The real child, stream assertions and
OS custody are unchanged. A native follow-up remains required.

The command payload exited 65, the Driver exited 2, and the observer correctly
reports `accepted=false`. The output and all 26 exported files were read back
and hash checked. The journal has eight length/CRC-validated records through
`REMOVED` and reports `cleanup=CONFIRMED` with the removed runtime. See the
[original export](original-export/) and [readback](original-export-readback.json).
After independent readback, the exact guest scope was removed
([receipt](guest-retire-result.png)); the [host receipt](host-cleanup.json)
confirms the owned stage and ISO were removed, original `sdc` restored and
foreign `sdb` preserved. No failed test is represented as a sensitivity RED
or product defect.
