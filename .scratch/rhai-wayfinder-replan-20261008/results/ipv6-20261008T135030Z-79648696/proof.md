# Native IPv6 exact-grant and peer-data proof

The new public Engine selectors in `net_connect` and `net_listen` execute on
native Darwin arm64 and Linux x86_64, Rust 1.77.2, with `net` and
`net,sync,no_index` (plus the recorded `testing-environ` verification feature).
Each selector/profile has an intended wrong-byte expectation RED101 and a
freshly compiled restored GREEN0 in one private native build scope. The two
platforms use identical committed-source archive, owned test patch and lock.
Original build artifacts, exact selectors, source/executable hashes, commands,
status, environment and independent observations remain in the result records.

Connect rejects default denial, another address family, another port, and a
listen-only grant without creating an independent peer. The exact numeric IPv6
connect grant delivers the script bytes to a real host listener; actual endpoints
are IPv6 and close is independently observed as EOF. Listen port0 requires its
own exact IPv6 grant; the OS-selected port is nonzero and accepted peer identity
matches the independent client. Script writes are read exactly by that client;
EOF and a fresh connection-refused result observe stream/listener closure.
Immediate rebind is deliberately not used as this oracle: an accepted TCP
connection may enter TIME_WAIT independently of listener-handle closure.

Both runtime/target/private-cache trees and exact owned empty outer scopes are
retired after original evidence export. Linux export files were independently
SHA-256 verified. Socket fixtures own OS-selected ports and bounded waits; no
shared service, global environment, foreign resource or production code changed.

Combined independent review accepted these exact native rows with no actionable
findings; see [review.md](review.md). Windows IPv6 and broader TCP/feature/release
rows remain open; this is not full package acceptance. Reuse accepted unchanged IPv4/coexistence/feature evidence.
