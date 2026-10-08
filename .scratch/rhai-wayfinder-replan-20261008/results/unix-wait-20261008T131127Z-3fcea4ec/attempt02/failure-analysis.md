# Attempt02: wrong selected wait overload

The selected public child was created, but child.wait(5) is not registered
with floats: the timed overload is FLOAT; INT exists only under no_float.
This is an invalid test invocation, not a product defect or the expected RED.
The corrected regression selects 5.0/0.0 or5/0 according to the enabled feature.
The full spawn_child/parse_options/ProcessChild::register/snapshot path and
fixture stdout/record/exit path were re-read. Saved original output remains.
No assertion RED or product acceptance is inferred from this attempt.
