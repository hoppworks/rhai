# Independent pre-execution review

The reviewer found no concrete false-success path in the Windows stream test or
frozen native preparation. Six cases exercise `run`, `run_raw`, and `spawn`
under DirectChild and Managed. A real child interleaves 512 flushed 8-KiB
chunks per stream and writes a separate receipt; parent assertions inspect
complete contents and an independently observed exact child exit. The test
verifies PID plus process creation time before permitting termination.

Twelve controls require the appropriate inverted stdout or stderr assertion,
exit 101, one failed libtest and child readback. GREEN requires all six
readbacks and seven passing tests. Cargo runs from the frozen source copy;
source, lock, toolchain, Driver and control files are bound. The Driver limit
is 180 seconds, observer limit 185 seconds and export limit 180 seconds.
Exceeding a limit is not acceptance. On failures before the exact child handle
is obtained or before terminal state, external Windows Job custody remains
necessary; that previously reviewed mechanism must be shown effective in this
run. No native execution or release acceptance is claimed by this review.
