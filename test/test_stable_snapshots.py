#!/usr/bin/env python3
"""
Acceptance tests for the snapshot stability protocol (igver 1.4.0, docs/plans/20260925_stable_snapshots_plan.md).

Author: Samuel Ahuno
Date: 2026-09-25
Purpose: written before the implementation; every stability test fails on 1.3.1.

The fake IGV models what probe 9 showed: a capture of a view is either "settled" (identical in every
process) or, when the test says so, "unsettled" (a stripe drawn over the settled image). Captures are
counted per view (goto) within one IGV process; `unsettled(call, goto, k)` picks which are unsettled.
"""

import hashlib
import os
import re
import shlex
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PIL import Image, ImageChops, ImageDraw

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import igver.cli
from igver import igver as core

REPO = Path(__file__).resolve().parent.parent
TEST_BAM = REPO / "test" / "test_tumor.bam"
UNSIZED_SVG = ('<?xml version="1.0"?>\n<svg xmlns="http://www.w3.org/2000/svg">'
               '<rect x="0" y="0" width="120" height="80" fill="#c0c0c0"/></svg>\n')


def _settled(goto):
    """The settled image of a view: a colour derived from the locus, identical in every 'process'."""
    h = hashlib.sha1(goto.encode()).digest()
    return Image.new('RGB', (120, 80), (h[0], h[1], h[2]))


def _unsettled(goto):
    img = _settled(goto)
    ImageDraw.Draw(img).rectangle([0, 10, 119, 12], fill=(0, 0, 0))  # a half-painted ruler row
    return img


def _locus_name(goto):
    m = re.match(r'^(.+):(\d+)-(\d+)$', goto)
    return f'chr{m.group(1)}_{int(m.group(2)):,}_{int(m.group(3)):,}' if m else goto


def _fake_igv(unsettled=lambda call, goto, k: False):
    """
    Fake `_run_until_stalled`: runs the batch; capture k (1-based, per view, per process) of view `goto`
    in IGV call number `call` is unsettled when unsettled(call, goto, k) is true.
    """
    state = {'call': 0}

    def fake(cmd, png_paths, stall_timeout, debug=False):
        state['call'] += 1
        call = state['call']
        batch = shlex.split(cmd.split(' -b ', 1)[1])[0]
        directory, goto, k = None, None, 0
        for line in open(batch).read().splitlines():
            if line.startswith('snapshotDirectory '):
                directory = shlex.split(line)[1]
            elif line.startswith('goto '):
                goto, k = line[len('goto '):], 0
            elif line == 'snapshot' or line.startswith('snapshot '):
                k += 1
                name = (_locus_name(goto) + '.png') if line == 'snapshot' else line[len('snapshot '):]
                img = _unsettled(goto) if unsettled(call, goto, k) else _settled(goto)
                path = os.path.join(directory, name)
                if name.endswith('.svg'):
                    Path(path).write_text(UNSIZED_SVG)
                else:
                    img.save(path)
        return True
    return fake


def _run(argv, fake, tmp_path, monkeypatch):
    monkeypatch.setenv('TMPDIR', str(tmp_path / 'tmpdir'))
    (tmp_path / 'tmpdir').mkdir(exist_ok=True)
    mock = Mock(side_effect=fake)
    code = 0
    with patch.object(sys, 'argv', ['igver'] + argv), patch('igver.igver._run_until_stalled', mock):
        try:
            igver.cli.main()
        except SystemExit as e:
            code = e.code
    return code, mock


def _same(path, image):
    with Image.open(path) as im:
        return ImageChops.difference(im.convert('RGB'), image).getbbox() is None


ARGS = ['-g', 'hg19', '--no-singularity']


class TestBlockShape:

    def _blocks(self, tmp_path, monkeypatch, fmt):
        monkeypatch.setenv('TMPDIR', str(tmp_path))
        batch, _ = core.create_batch_script([str(TEST_BAM)], ['8:1-100'], str(tmp_path / 'o'),
                                            output_format=fmt)
        return core._split_batch(open(batch).read())[1]

    def test_png_block_has_post_capture(self, tmp_path, monkeypatch):
        block = self._blocks(tmp_path, monkeypatch, 'png')[0]
        i = block.index('snapshot 8-1-100.png')
        assert block[i + 1].startswith('snapshotDirectory ') and 'igver_verify_' in block[i + 1]
        assert block[i + 2] == 'snapshot igver_post.png'
        assert block[i + 3].startswith('snapshotDirectory ') and block[-1] == 'gotoimmediate All'
        assert core._snapshot_name(block) == '8-1-100.png'

    def test_svg_block_has_pre_and_post_captures(self, tmp_path, monkeypatch):
        block = self._blocks(tmp_path, monkeypatch, 'svg')[0]
        i = block.index('snapshot 8-1-100.svg')
        assert 'snapshot igver_pre.png' in block[:i] and 'snapshot igver_post.png' in block[i:]
        assert core._snapshot_name(block) == '8-1-100.svg'


class TestStability:

    def test_stable_first_time(self, tmp_path, monkeypatch):
        out = tmp_path / 'o'
        code, mock = _run(['-i', str(TEST_BAM), '-r', '8:1-100', '19:5-50', '-o', str(out)] + ARGS,
                          _fake_igv(), tmp_path, monkeypatch)
        assert code == 0 and mock.call_count == 1
        assert _same(out / '8-1-100.png', _settled('8:1-100'))

    def test_unsettled_real_capture_is_rerendered(self, tmp_path, monkeypatch, capsys):
        # capture 2 of the view = the real snapshot; unsettled in the first IGV process only
        out = tmp_path / 'o'
        fake = _fake_igv(lambda call, goto, k: call == 1 and goto == '19:5-50' and k == 2)
        code, mock = _run(['-i', str(TEST_BAM), '-r', '8:1-100', '19:5-50', '-o', str(out)] + ARGS,
                          fake, tmp_path, monkeypatch)
        assert code == 0 and mock.call_count == 2
        assert _same(out / '19-5-50.png', _settled('19:5-50'))
        assert _same(out / '8-1-100.png', _settled('8:1-100'))
        captured = capsys.readouterr()
        assert '1 of 2' in captured.out + captured.err  # the re-render rate is reported

    def test_rerender_only_the_unstable_region(self, tmp_path, monkeypatch):
        out = tmp_path / 'o'
        seen = []
        base = _fake_igv(lambda call, goto, k: call == 1 and goto == '19:5-50' and k == 2)

        def spy(cmd, png_paths, stall_timeout, debug=False):
            batch = shlex.split(cmd.split(' -b ', 1)[1])[0]
            seen.append([l for l in open(batch).read().splitlines() if l.startswith('goto ')])
            return base(cmd, png_paths, stall_timeout, debug)
        _run(['-i', str(TEST_BAM), '-r', '8:1-100', '19:5-50', '-o', str(out)] + ARGS, spy, tmp_path, monkeypatch)
        assert seen == [['goto 8:1-100', 'goto 19:5-50'], ['goto 19:5-50']]

    def test_never_stable_is_kept_with_warning(self, tmp_path, monkeypatch, capsys):
        out = tmp_path / 'o'
        fake = _fake_igv(lambda call, goto, k: k == 2)  # the real capture is always unsettled
        code, mock = _run(['-i', str(TEST_BAM), '-r', '8:1-100', '-o', str(out)] + ARGS,
                          fake, tmp_path, monkeypatch)
        assert code == 0
        assert mock.call_count == 3  # first pass + 2 stability passes, no more
        assert (out / '8-1-100.png').exists()
        captured = capsys.readouterr()
        assert 'not stable' in captured.out + captured.err and '8-1-100.png' in captured.out + captured.err

    def test_svg_uses_pre_and_post(self, tmp_path, monkeypatch):
        # SVG block captures per view: 1 locus, 2 pre, 3 real (svg), 4 post
        out = tmp_path / 'o'
        fake = _fake_igv(lambda call, goto, k: call == 1 and k == 2)
        code, mock = _run(['-i', str(TEST_BAM), '-r', '8:1-100', '-o', str(out), '-f', 'svg'] + ARGS,
                          fake, tmp_path, monkeypatch)
        assert code == 0 and mock.call_count == 2
        assert 'viewBox="0 0 120 80"' in (out / '8-1-100.svg').read_text()

    def test_unsettled_locus_capture_does_not_trigger_rerender(self, tmp_path, monkeypatch):
        out = tmp_path / 'o'
        fake = _fake_igv(lambda call, goto, k: k == 1)  # only the first (locus) capture is unsettled
        code, mock = _run(['-i', str(TEST_BAM), '-r', '8:1-100', '-o', str(out)] + ARGS,
                          fake, tmp_path, monkeypatch)
        assert code == 0 and mock.call_count == 1

    def test_locus_verification_ignores_stability_captures(self, tmp_path, monkeypatch):
        out = tmp_path / 'o'
        code, _ = _run(['-i', str(TEST_BAM), '-r', 'TP53', '-o', str(out)] + ARGS,
                       _fake_igv(), tmp_path, monkeypatch)
        assert code == 0 and (out / 'TP53.png').exists()
        assert not [d for d in os.listdir(tmp_path / 'tmpdir') if d.startswith('igver_')]

    def test_images_identical_helper(self, tmp_path):
        from igver.igver import images_identical
        a, b, c = tmp_path / 'a.png', tmp_path / 'b.png', tmp_path / 'c.png'
        _settled('x').save(a)
        _settled('x').save(b)
        _unsettled('x').save(c)
        assert images_identical(str(a), str(b)) and not images_identical(str(a), str(c))
