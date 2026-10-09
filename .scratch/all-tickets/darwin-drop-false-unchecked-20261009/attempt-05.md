# X28 attempt 05 preparation stop

No test ran. Cargo launched from the project checkout instead of the owned
source archive and rejected the archived lock context (`Cargo.lock needs to be
updated`); the wrapper's expected RED status 101 therefore came from setup, not
the test assertion. Runner status was 1, the exact owned scope was retired, and
no child/test fixture or reusable build was created. The combined harness now
sets its working directory to the owned source archive before invoking Cargo.
