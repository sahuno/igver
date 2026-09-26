"""
Tests for batch splitting, missing-only retry, and --jobs parallel chunking.
Author: Samuel Ahuno
Date: 2026-09-09
Purpose: verify run_igv re-renders only missing regions, load_screenshots(jobs=N) fans out N IGV
processes, and the stall watchdog kills an IGV that stops producing snapshots.
"""
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import igver
from igver.igver import _split_batch, _write_batch, _snapshot_name, _run_until_stalled, run_igv

TEST_BAM = os.path.join(os.path.dirname(__file__), 'test_tumor.bam')
REGIONS = ['chr1:100-200', 'chr2:300-400', 'chr3:500-600']


def _snapshot_files(batch_path):
    """Return the snapshot filenames a batch file would write."""
    with open(batch_path) as f:
        _, blocks = _split_batch(f.read())
    return [_snapshot_name(b) for b in blocks]


def test_split_batch_roundtrip(tmp_path):
    batch, png_paths = igver.create_batch_script([TEST_BAM], REGIONS, str(tmp_path), genome='hg19',
                                                 color_by='TAG HP')
    with open(batch) as f:
        text = f.read()
    header, blocks = _split_batch(text)
    assert header[0] == 'new' and any(line.startswith('load ') for line in header)
    assert len(blocks) == 3
    assert [_snapshot_name(b) for b in blocks] == [os.path.basename(p) for p in png_paths]
    # igver 1.3.1: each block ends with its snapshot and then the `gotoimmediate All` view reset
    assert all(b[0].startswith('goto ') and b[-2].startswith('snapshot ') and b[-1] == 'gotoimmediate All'
               for b in blocks)
    out = tmp_path / 'rt.batch'
    _write_batch(str(out), header, blocks)
    assert out.read_text() == text


def test_retry_rerenders_only_missing(tmp_path):
    batch, png_paths = igver.create_batch_script([TEST_BAM], REGIONS, str(tmp_path), genome='hg19')
    seen = []

    def fake_igv(cmd, png_paths_arg, stall_timeout, debug=False):
        # First call: render all but the middle region. Second call: render everything requested.
        seen.append(_snapshot_files(batch))
        for name in seen[-1]:
            if len(seen) == 1 and name == os.path.basename(png_paths[1]):
                continue
            open(os.path.join(str(tmp_path), name), 'w').close()
        return True

    with patch('igver.igver._run_until_stalled', side_effect=fake_igv):
        run_igv(batch, png_paths, use_singularity=False)

    assert len(seen) == 2
    assert seen[0] == [os.path.basename(p) for p in png_paths]
    assert seen[1] == [os.path.basename(png_paths[1])]  # retry covered only the missing one
    assert all(os.path.exists(p) for p in png_paths)


def test_retry_gives_up_after_two_attempts(tmp_path):
    batch, png_paths = igver.create_batch_script([TEST_BAM], REGIONS[:1], str(tmp_path), genome='hg19')
    with patch('igver.igver._run_until_stalled', return_value=True) as m:
        with pytest.raises(RuntimeError):
            run_igv(batch, png_paths, use_singularity=False)
    assert m.call_count == 2


def test_jobs_splits_regions_across_processes(tmp_path):
    batches = []

    def fake_igv(cmd, png_paths_arg, stall_timeout, debug=False):
        batch = cmd.split(' -b ')[1].split()[0]
        names = _snapshot_files(batch)
        batches.append(names)
        for name in names:
            open(os.path.join(str(tmp_path), name), 'w').close()
        return True

    with patch('igver.igver._run_until_stalled', side_effect=fake_igv):
        out = igver.load_screenshots([TEST_BAM], REGIONS, str(tmp_path), genome='hg19',
                                     use_singularity=False, load_figures=False, jobs=2)

    assert len(batches) == 2
    assert sorted(len(b) for b in batches) == [1, 2]
    assert sorted(n for b in batches for n in b) == sorted(os.path.basename(p) for p in out)
    assert all(os.path.exists(p) for p in out)
    assert not [f for f in os.listdir(tmp_path) if f.endswith('.batch')]  # all batch files cleaned up


def test_stall_watchdog_kills_process_group(tmp_path):
    import subprocess, time
    marker = tmp_path / 'child.pid'
    # Parent shell spawns a grandchild (like xvfb-run -> java); watchdog must kill both.
    cmd = f"sh -c 'sleep 300 & echo $! > {marker}; wait'"
    t0 = time.time()
    finished = _run_until_stalled(cmd, [str(tmp_path / 'never.png')], stall_timeout=1)
    assert finished is False
    assert time.time() - t0 < 30
    time.sleep(0.5)
    pid = int(marker.read_text())
    assert subprocess.run(['kill', '-0', str(pid)], capture_output=True).returncode != 0, "grandchild survived"


def test_stall_watchdog_resets_on_progress(tmp_path):
    import time
    out = tmp_path / 'a.png'
    # Produce a snapshot after 2s, then hang. stall_timeout=3 must not fire before progress at t=2,
    # and must fire ~3s after it, so total runtime lands in roughly [5, 20] seconds.
    cmd = f"sleep 2; touch {out}; sleep 300"
    t0 = time.time()
    finished = _run_until_stalled(cmd, [str(out)], stall_timeout=3)
    elapsed = time.time() - t0
    assert finished is False and out.exists()
    assert 5 <= elapsed <= 20, elapsed


def test_stall_timeout_disabled_waits_for_exit(tmp_path):
    out = tmp_path / 'a.png'
    assert _run_until_stalled(f"touch {out}", [str(out)], stall_timeout=0) is True
