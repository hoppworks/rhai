# Executable TCP example and metadata proof

Native macOS27 arm64, Rust1.93.0. Base1964bb93; only Cargo example admission, examples/net.rs, package documentation and tests/net_metadata.rs changed. Public seam: runnable Cargo example -> Engine registered NetPackage -> actual loopback TCP peer. No new production API behavior.

Run: python3 /Users/hoppworks/projects/agent-skills/tools/run_scoped.py --timeout900 -- bash .scratch/tcp-docs-example/run-proof.sh (actual option spelling --timeout 900). Private copied source, Cargo home/target, jobs2, debug0, one successful reused build invocation. Original15:40–16:10UTC package unchanged.

First two launches failed before Cargo because private mutation anchor did not match rustfmt output; initial setup error plus one unsuccessful recovery, not failed API corrections. Third launch reached the intended wrong independent peer assertion: actual ping [112,105,110,103] versus pang [112,97,110,103], status101. Restored tracked example passed status0, peer observed ping and script observed pong after shutdown_write/EOF. The same example passed with net,no_object,metadata using explicit function calls. Both metadata targets passed1/1; public JSON metadata includes documented callable names and NetStream/NetListener/NetError. Exact commands/statuses/logs are adjacent, environment.log records host/compiler.

Sampled whole private runtime peak 649,688 KiB at one-second intervals, below2GiB; true peak storage and memory unmeasured. All setup and final runtimes were read back absent. Final exact runtime /var/folders/yk/m4dzf0ss5x9f4j4z3xb2rrv40000gn/T/agent-build-21lztwm3 absent after successful scoped cleanup. Threads own bounded accept and socket read/write deadlines and panic-safe joins; no shared service/process mutation. No persistent output/build retained.

This proves native macOS runnable documentation and metadata registration under net,metadata and net,no_object,metadata only. It does not replace complete operation/feature matrices, process, Linux, Windows or MSRV acceptance. Existing accepted TCP behavior evidence applies unchanged because only documentation/example/tests changed.
