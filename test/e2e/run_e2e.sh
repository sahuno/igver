#!/usr/bin/env bash
# Author: Samuel Ahuno
# Date: 2026-09-25
# Purpose: run the igver end-to-end suite (test/e2e/cases.tsv) in one run mode against real IGV, with a timestamped log.
#
# Usage: test/e2e/run_e2e.sh host|image [e2e_runner.py options, e.g. --cases E1,E2a --no-repo-bind --tag baseline]
# Submit full runs with sbatch (plan §3.2), e.g.:
#   sbatch -p cpushort --exclude=isca071 -c 2 --mem=16G -t 01:30:00 -o test/e2e/logs/slurm_%j.out test/e2e/run_e2e.sh host
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# sbatch runs a spooled copy of this script; fall back to the submit directory (the repo root)
[ -f "$HERE/e2e_runner.py" ] || HERE="${SLURM_SUBMIT_DIR:?not in test/e2e and no SLURM_SUBMIT_DIR}/test/e2e"
MODE="${1:?usage: run_e2e.sh host|image [runner options]}"
shift
mkdir -p "$HERE/logs"
TS="$(date '+%Y%m%d_%H%M%S')"
LOG_FILE="$HERE/logs/e2e_${MODE}_${TS}.log"
exec > >(tee -a "$LOG_FILE") 2>&1
log_msg() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

unset APPTAINER_BIND SINGULARITY_BIND
export APPTAINER_CACHEDIR=/data1/greenbab/users/ahunos/apptainer_cache
PY=/home/ahunos/miniforge3/envs/igver/bin/python

log_msg "=== igver e2e: mode=$MODE args=$* ==="
log_msg "host=$(hostname) job=${SLURM_JOB_ID:-none} cwd=$(pwd) log=$LOG_FILE"
log_msg "git: $(git -C "$HERE/../.." rev-parse --short HEAD) $(git -C "$HERE/../.." status --porcelain | wc -l) uncommitted path(s)"
log_msg "PYTHONPATH=${PYTHONPATH:-unset}"
log_msg "python: $($PY --version 2>&1); igver import: $($PY -c 'import igver; print(igver.__file__)' 2>&1)"

START=$(date +%s)
"$PY" "$HERE/e2e_runner.py" --mode "$MODE" --results "$HERE/logs/e2e_${MODE}_${TS}.tsv" "$@"
STATUS=$?
log_msg "runner exit=$STATUS; results: $HERE/logs/e2e_${MODE}_${TS}.tsv; completed in $(( $(date +%s) - START ))s"
[ "$STATUS" -eq 0 ] && log_msg "=== DONE: $(basename "$0") completed successfully ===" \
                   || log_msg "=== DONE: $(basename "$0") finished with failures ==="
exit "$STATUS"
