# Independent diagnosis review

The reviewer checked the original twelve failed controls and
`src/eval/data_check.rs`. Rhai sums both returned string lengths or both Blob
sizes within the result map. The original 4 MiB plus 1 KiB Engine limit was
therefore insufficient for two four-MiB streams. The observed text and Blob
`ErrorDataTooLarge` results occurred before the intended wrong assertions.

The follow-up test sets the Engine aggregate limits to 8 MiB plus 2 KiB while
retaining the same per-stream `max_output`. This diagnosis and correction do
not by themselves prove native behavior; the first run remains unaccepted and
requires the separate follow-up execution and review.
