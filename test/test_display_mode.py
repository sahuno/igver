# Author: Samuel Ahuno
# Date: 2026-09-25
# Purpose: -d/--overlap-display must target alignment tracks by name, never annotation tracks.
"""
A bare `squish`/`expand` in an IGV batch applies to every track; a squished or expanded
annotation track (the genome's RefSeq track, BED files) fills the panel and hides the
tracks below it. These tests pin the per-track behaviour.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from igver import igver  # noqa: E402


def _batch_lines(tmp_path, paths, regions, **kwargs):
    batch, _ = igver.create_batch_script(paths, regions, str(tmp_path), genome='hg38', **kwargs)
    with open(batch) as f:
        return f.read().splitlines()


class TestDisplayCommands:
    def test_squish_targets_only_alignments(self):
        paths = ['/d/s1.bam', '/d/genes.bed', '/d/s2.cram', '/d/cov.bw']
        assert igver._display_commands(paths, 'squish') == 'squish s1.bam\nsquish s2.cram'

    def test_expand_emits_nothing(self):
        assert igver._display_commands(['/d/s1.bam'], 'expand') == ''

    def test_annotation_only_emits_nothing(self):
        assert igver._display_commands(['/d/a.bed', '/d/b.bed'], 'squish') == ''

    def test_extension_case_insensitive_and_deduplicated(self):
        paths = ['/x/S.BAM', '/y/S.BAM', '/z/r.sam']
        assert igver._display_commands(paths, 'collapse') == 'collapse S.BAM\ncollapse r.sam'

    def test_whitespace_name_skipped_with_warning(self, capsys):
        assert igver._display_commands(['/d/my sample.bam'], 'squish') == ''
        assert 'whitespace' in capsys.readouterr().out


class TestBatchScript:
    def test_no_bare_display_command(self, tmp_path):
        lines = _batch_lines(tmp_path, ['/d/s1.bam', '/d/genes.bed'], ['chr1:100-200'])
        assert 'squish' not in lines
        assert 'squish s1.bam' in lines

    def test_bed_only_has_no_display_command(self, tmp_path):
        lines = _batch_lines(tmp_path, ['/d/genes.bed'], ['chr1:100-200'])
        assert not any(line.split()[0] in ('squish', 'collapse', 'expand') for line in lines if line)

    @pytest.mark.parametrize('mode', ['collapse', 'squish'])
    def test_mode_emitted_per_region(self, tmp_path, mode):
        lines = _batch_lines(tmp_path, ['/d/s1.bam'], ['chr1:100-200', 'chr2:300-400'],
                             overlap_display=mode)
        # igver 1.4.0: applied in every region block twice (initial layout + re-layout once loaded)
        _, blocks = igver._split_batch('\n'.join(lines))
        assert len(blocks) == 2 and all(b.count(f'{mode} s1.bam') == 2 for b in blocks)
        assert lines.count(f'{mode} s1.bam') == 4 and mode not in lines  # never a bare command
