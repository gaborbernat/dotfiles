# Before/After Examples

## Stock framing

**Before:** "Here's what changed: the retry loop now stops after three attempts. This matters because the old loop could
run forever."

**After:** "The retry loop now stops after three attempts. The old loop could retry forever."

The revision keeps both facts and removes the setup and emphasis.

## Useful contrast

**Before:** "The formatter did not fail. The generated file had a stale checksum."

**After:** "The generated file had a stale checksum; the formatter completed."

Both facts matter. Cutting every negative sentence would erase the distinction.

## Evidence before precision

**Source:** A benchmark reports startup time falling from 5.0 to 3.0 seconds; no other workload was measured.

**Before:** "The patch dramatically improves performance everywhere."

**After:** "In the benchmark, startup time fell from 5.0 to 3.0 seconds."

The edit narrows the claim to the available measurement. Without a benchmark, omit the numerical claim.
