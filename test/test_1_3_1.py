#!/usr/bin/env python3
"""
Acceptance tests for igver 1.3.1: unknown gene/contig detection (U1) and working -f pdf (U2).

Author: Samuel Ahuno
Date: 2026-09-25
Purpose: written before the fixes (docs/plans/20260925_1_3_1_plan.md); every U1/U2 test fails on 1.3.0.

A fake IGV interprets the batch the way IGV 2.19.8 does (probes 2026-09-25): a bare `snapshot` is
named after the current locus, e.g. `chr8_1_100.png`, split view `a | b.png`, whole genome
`All_1_3,095,677.png`. New symbols are imported inside the tests (module collects on 1.3.0).
"""

import os
import re
import shlex
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import igver.cli
from igver import igver as core

REPO = Path(__file__).resolve().parent.parent
TEST_BAM = REPO / "test" / "test_tumor.bam"
WHOLE_GENOME = 'All_1_3,095,677'
# An IGV SVG as 2.19.8 writes it: no width, height or viewBox on the root element
UNSIZED_SVG = ('<?xml version="1.0"?>\n<svg xmlns="http://www.w3.org/2000/svg" fill="black">'
               '<rect x="0" y="0" width="300" height="200" fill="#c0c0c0"/>'
               '<text x="20" y="40" font-size="20">igver</text></svg>\n')


def _igv_locus(goto_arg):
    """What IGV shows after a successful goto: one frame per locus, commas in coordinates."""
    frames = []
    for token in goto_arg.split():
        m = re.match(r'^(.+):(\d+)-(\d+)$', token)
        if not m:
            return token  # a gene name IGV found; tests pass it via `found`
        chrom = m.group(1) if m.group(1).startswith('chr') else 'chr' + m.group(1)
        frames.append(f'{chrom}_{int(m.group(2)):,}_{int(m.group(3)):,}')
    return ' | '.join(frames)


def _fake_igv_factory(found=None, write_verify=True, width=300, height=200):
    """
    Build a fake `_run_until_stalled` that executes the batch like IGV.

    Parameters:
        found (dict): goto argument -> locus string IGV ends up on (default: _igv_locus).
        write_verify (bool): write the bare verification snapshot.
        width, height (int): pixel size of every PNG written.
    """
    found = found or {}

    def fake(cmd, png_paths, stall_timeout, debug=False):
        batch = shlex.split(cmd.split(' -b ', 1)[1])[0]
        current, directory = 'All', None
        for line in open(batch).read().splitlines():
            if line.startswith('snapshotDirectory '):
                directory = shlex.split(line)[1]
            elif line.startswith('gotoimmediate '):
                current = WHOLE_GENOME if line.split()[1] == 'All' else line.split(None, 1)[1]
            elif line.startswith('goto '):
                arg = line[len('goto '):]
                current = found.get(arg, _igv_locus(arg))
            elif line == 'snapshot':
                if write_verify:
                    Image.new('RGB', (width, height), 'white').save(
                        os.path.join(directory, current.replace(':', '_').replace('-', '_') + '.png'))
            elif line.startswith('snapshot '):
                name = line[len('snapshot '):]
                path = os.path.join(directory, name)
                if name.endswith('.svg'):
                    Path(path).write_text(UNSIZED_SVG)
                else:
                    Image.new('RGB', (width, height), 'gray').save(path)
        return True
    return fake


def _run(argv, fake, tmp_path, monkeypatch):
    """Run the CLI with TMPDIR inside tmp_path; returns (exit code or 0, fake mock)."""
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


def _files(path):
    return sorted(f for f in os.listdir(path) if not f.endswith('.batch'))


# --------------------------------------------------------------------------------------------
# U1 - unknown gene / contig / out-of-range locus
# --------------------------------------------------------------------------------------------

class TestU1BatchShape:

    def test_block_has_verification_and_reset(self, tmp_path, monkeypatch):
        monkeypatch.setenv('TMPDIR', str(tmp_path))
        batch, png = core.create_batch_script([str(TEST_BAM)], ['8:1-100', 'TP53'], str(tmp_path / 'o'))
        header, blocks = core._split_batch(open(batch).read())
        assert len(blocks) == 2
        for i, block in enumerate(blocks):
            assert block[0].startswith('goto ')
            assert block[-1] == 'gotoimmediate All'
            assert block[-2] == f'snapshot {os.path.basename(png[i])}'
            v = block.index('snapshot')
            verify_dir = shlex.split(block[v - 1])[1]
            assert block[v - 1].startswith('snapshotDirectory ') and os.path.isdir(verify_dir)
            assert os.path.basename(verify_dir) == str(i)
            assert os.path.basename(os.path.dirname(verify_dir)).startswith('igver_verify_')
            assert block[v + 1] == f'snapshotDirectory {os.path.abspath(tmp_path / "o")}'

    def test_snapshot_name_with_trailing_reset(self):
        block = ['goto chr1:1-2', 'snapshotDirectory /v/0', 'snapshot', 'snapshotDirectory /o',
                 'snapshot chr1-1-2.png', 'gotoimmediate All']
        assert core._snapshot_name(block) == 'chr1-1-2.png'


class TestU1Verification:

    def test_correct_loci_succeed_and_clean_up(self, tmp_path, monkeypatch):
        out = tmp_path / 'o'
        code, _ = _run(['-i', str(TEST_BAM), '-r', '8:1-100', '19:5-50', '-o', str(out), '-g', 'hg19',
                        '--no-singularity'], _fake_igv_factory(), tmp_path, monkeypatch)
        assert code == 0
        assert _files(out) == ['19-5-50.png', '8-1-100.png']
        assert not [d for d in os.listdir(tmp_path / 'tmpdir') if d.startswith('igver_')]

    def test_unknown_after_good_region_fails_and_removes_wrong_snapshot(self, tmp_path, monkeypatch, capsys):
        # IGV keeps the previous view on a failed goto; with the reset it lands on the whole genome
        out = tmp_path / 'o'
        found = {'NOSUCH:1-100': WHOLE_GENOME}
        code, _ = _run(['-i', str(TEST_BAM), '-r', '8:1-100', 'NOSUCH:1-100', '-o', str(out), '-g', 'hg19',
                        '--no-singularity'], _fake_igv_factory(found), tmp_path, monkeypatch)
        assert code == 1
        assert _files(out) == ['8-1-100.png']
        err = capsys.readouterr().err
        assert 'NOSUCH:1-100' in err and 'could not find' in err

    def test_unknown_gene_fails(self, tmp_path, monkeypatch, capsys):
        out = tmp_path / 'o'
        code, _ = _run(['-i', str(TEST_BAM), '-r', 'NOTAGENE123', '-o', str(out), '-g', 'hg19',
                        '--no-singularity'], _fake_igv_factory({'NOTAGENE123': WHOLE_GENOME}),
                       tmp_path, monkeypatch)
        assert code == 1 and _files(out) == []
        assert 'NOTAGENE123' in capsys.readouterr().err

    def test_found_gene_succeeds(self, tmp_path, monkeypatch):
        out = tmp_path / 'o'
        code, _ = _run(['-i', str(TEST_BAM), '-r', 'TP53', '-o', str(out), '-g', 'hg19', '--no-singularity'],
                       _fake_igv_factory({'TP53': 'chr17_7,569,739_7,592,808'}), tmp_path, monkeypatch)
        assert code == 0 and _files(out) == ['TP53.png']

    def test_split_view_dropped_locus_fails(self, tmp_path, monkeypatch, capsys):
        out = tmp_path / 'o'
        found = {'8:1-100 NOSUCH:1-100': 'chr8_1_100'}
        code, _ = _run(['-i', str(TEST_BAM), '-r', '8:1-100 NOSUCH:1-100', '-o', str(out), '-g', 'hg19',
                        '--no-singularity'], _fake_igv_factory(found), tmp_path, monkeypatch)
        assert code == 1 and _files(out) == []
        assert 'NOSUCH:1-100' in capsys.readouterr().err

    def test_whole_genome_requested_is_allowed(self, tmp_path, monkeypatch):
        out = tmp_path / 'o'
        code, _ = _run(['-i', str(TEST_BAM), '-r', 'All', '-o', str(out), '-g', 'hg19', '--no-singularity'],
                       _fake_igv_factory({'All': WHOLE_GENOME}), tmp_path, monkeypatch)
        assert code == 0 and _files(out) == ['All.png']

    def test_contig_starting_with_all_is_not_whole_genome(self, tmp_path, monkeypatch):
        out = tmp_path / 'o'
        code, _ = _run(['-i', str(TEST_BAM), '-r', 'Allo1:1-100', '-o', str(out), '-g', 'hg19',
                        '--no-singularity'], _fake_igv_factory({'Allo1:1-100': 'Allo1_1_100'}),
                       tmp_path, monkeypatch)
        assert code == 0

    def test_missing_verification_snapshot_only_warns(self, tmp_path, monkeypatch, capsys):
        out = tmp_path / 'o'
        code, _ = _run(['-i', str(TEST_BAM), '-r', '8:1-100', '-o', str(out), '-g', 'hg19',
                        '--no-singularity'], _fake_igv_factory(write_verify=False), tmp_path, monkeypatch)
        assert code == 0 and _files(out) == ['8-1-100.png']

    def test_missing_verification_warning_text(self, tmp_path, monkeypatch, capsys):
        out = tmp_path / 'o'
        _run(['-i', str(TEST_BAM), '-r', '8:1-100', '-o', str(out), '-g', 'hg19', '--no-singularity'],
             _fake_igv_factory(write_verify=False), tmp_path, monkeypatch)
        captured = capsys.readouterr()
        assert 'could not verify' in (captured.out + captured.err)

    def test_parallel_jobs_report_the_bad_region(self, tmp_path, monkeypatch, capsys):
        out = tmp_path / 'o'
        found = {'NOSUCH:1-100': WHOLE_GENOME}
        code, mock = _run(['-i', str(TEST_BAM), '-r', '8:1-100', 'NOSUCH:1-100', '-o', str(out), '-g', 'hg19',
                           '--no-singularity', '-j', '2'], _fake_igv_factory(found), tmp_path, monkeypatch)
        assert mock.call_count == 2
        assert code == 1 and _files(out) == ['8-1-100.png']
        assert 'NOSUCH:1-100' in capsys.readouterr().err

    def test_no_whole_genome_warning_any_more(self, tmp_path, capsys):
        core._get_paths_and_regions(['TP53'], output_dir=str(tmp_path))
        assert 'whole-genome' not in capsys.readouterr().out


# --------------------------------------------------------------------------------------------
# U2 - -f pdf / sized SVG
# --------------------------------------------------------------------------------------------

class TestU2SvgAndPdf:

    def test_unsized_svg_gets_size(self, tmp_path):
        from igver.igver import ensure_svg_size
        svg = tmp_path / 'a.svg'
        svg.write_text(UNSIZED_SVG)
        assert ensure_svg_size(str(svg), 300, 200) is True
        root = re.search(r'<svg\b[^>]*>', svg.read_text()).group(0)
        assert 'width="300"' in root and 'height="200"' in root and 'viewBox="0 0 300 200"' in root

    def test_sized_svg_untouched(self, tmp_path):
        from igver.igver import ensure_svg_size
        svg = tmp_path / 'a.svg'
        text = UNSIZED_SVG.replace('<svg ', '<svg width="10" height="20" ')
        svg.write_text(text)
        assert ensure_svg_size(str(svg), 300, 200) is False
        assert svg.read_text() == text

    @pytest.mark.parametrize('dpi,media_box', [(None, b'0 0 72 48'), ('96', b'0 0 225 150')])
    def test_cli_pdf_is_written_with_the_canvas_size(self, tmp_path, monkeypatch, dpi, media_box):
        # the page is the canvas at --dpi (default 300): 300x200 px -> 1x0.67 in = 72x48 pt
        out = tmp_path / 'o'
        argv = ['-i', str(TEST_BAM), '-r', '8:1-100', '-o', str(out), '-g', 'hg19', '--no-singularity', '-f', 'pdf']
        code, _ = _run(argv + (['--dpi', dpi] if dpi else []), _fake_igv_factory(width=300, height=200),
                       tmp_path, monkeypatch)
        assert code == 0
        assert _files(out) == ['8-1-100.pdf', '8-1-100.svg']
        pdf = (out / '8-1-100.pdf').read_bytes()
        assert pdf.startswith(b'%PDF')
        assert re.search(rb'/MediaBox \[ ?' + media_box + rb' ?\]', pdf), pdf[:400]
        assert b'/Font' in pdf  # the fixture's text was rendered, so the page is not empty

    def test_cli_svg_is_sized(self, tmp_path, monkeypatch):
        out = tmp_path / 'o'
        code, _ = _run(['-i', str(TEST_BAM), '-r', '8:1-100', '-o', str(out), '-g', 'hg19', '--no-singularity',
                        '-f', 'svg'], _fake_igv_factory(width=300, height=200), tmp_path, monkeypatch)
        assert code == 0 and _files(out) == ['8-1-100.svg']
        assert 'viewBox="0 0 300 200"' in (out / '8-1-100.svg').read_text()

    def test_dockerfile_installs_cairosvg(self):
        assert 'python-cairosvg' in (REPO / 'docker' / 'Dockerfile').read_text()
