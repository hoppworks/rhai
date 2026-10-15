# Attempt 04

Runs only the restored post-reap GREEN missing from attempt 02. Attempt 03 did not start Cargo because the launcher inherited a non-login PATH. This attempt invokes the launcher from Daniel's login environment, then uses the same scoped runner and checks exit status, selector, Cargo summary, and independent process/pipe observations.
