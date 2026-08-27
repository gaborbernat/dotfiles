#!/bin/bash
# Prints the cargo build job count for this machine on stdout.
#
# Two ceilings apply, and the lower one wins. Cores: rustc spends most of a build
# in LLVM, which scales with single-core throughput, so a job that lands on an
# efficiency core returns a fraction of a job's speedup for a full job's memory.
# Memory: each concurrent rustc keeps its crate's IR resident and peaks in the
# GBs, and once the working set passes RAM macOS compresses pages instead of
# swapping, so decompression then competes for the cores the build is using.
set -euo pipefail

RESERVED_GB=4
GB_PER_JOB=2

if [[ "$(uname -s)" == "Darwin" ]]; then
    # perflevel0 is the performance cluster and is absent on Intel, where every
    # core is one tier and the physical count is the right ceiling.
    cores=$(sysctl -n hw.perflevel0.logicalcpu 2>/dev/null || sysctl -n hw.physicalcpu)
    ram_gb=$(($(sysctl -n hw.memsize) / 1073741824))
else
    cores=$(nproc)
    ram_gb=$(($(awk '/^MemTotal:/ {print $2}' /proc/meminfo) / 1048576))
fi

jobs=$(((ram_gb - RESERVED_GB) / GB_PER_JOB))
if ((jobs > cores)); then
    jobs=$cores
fi
if ((jobs < 1)); then
    jobs=1
fi

echo "$jobs"
