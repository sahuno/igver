#!/usr/bin/env python3
"""
CLI-level integration test for the -f/--format option.
Author: Samuel Ahuno
Purpose: verify `igver -f png|svg|pdf` plumbs the format through cli.main -> load_screenshots ->
         create_batch_script. The API-level format behaviour is covered by test_output_formats.py;
         this file only covers the CLI wiring.

IGV is never launched: igver.igver._run_until_stalled is patched out.
"""

import os
import sys
from unittest.mock import patch, Mock

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import igver.cli

TEST_BAM = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_tumor.bam')
REGION = 'chr1:1000000-2000000'


def _run_cli(argv, captured):
    """Run cli.main() in-process with a fake IGV that records the batch it was handed."""
    def fake_igv(cmd, png_paths, stall_timeout, debug=False):
        # run_igv deletes the batch file on success, so read it now.
        batch_path = cmd.split(' -b ')[1].split()[0]
        captured['cmd'] = cmd
        captured['batch'] = open(batch_path).read()
        captured.setdefault('png_paths', []).extend(png_paths)
        for png_path in png_paths:
            open(png_path, 'w').close()
        return True

    def fake_svg2pdf(svg_paths, remove_svg, dpi, debug):
        pdf_paths = [p[:-4] + '.pdf' for p in svg_paths]
        for pdf_path in pdf_paths:
            open(pdf_path, 'w').close()
        return pdf_paths

    fake = Mock(side_effect=fake_igv)
    with patch.object(sys, 'argv', argv), \
         patch('igver.igver._run_until_stalled', fake), \
         patch('igver.igver._convert_svg_to_pdf', side_effect=fake_svg2pdf):
        igver.cli.main()
    return fake


# pdf is requested from IGV as svg and converted afterwards: the batch asks for svg, disk gets pdf
@pytest.mark.parametrize('fmt,expected_ext,disk_ext',
                         [('png', 'png', 'png'), ('svg', 'svg', 'svg'), ('pdf', 'svg', 'pdf')])
def test_cli_format_flag(tmp_path, fmt, expected_ext, disk_ext):
    """`-f FORMAT` reaches the IGV batch script, the snapshot paths, and the final file on disk."""
    captured = {}
    fake = _run_cli(
        ['igver', '-i', TEST_BAM, '-r', REGION, '-o', str(tmp_path),
         '-f', fmt, '--no-singularity'],
        captured,
    )

    assert fake.call_count == 1
    expected_name = f'chr1-1000000-2000000.{expected_ext}'
    assert f'snapshot {expected_name}' in captured['batch']
    assert [os.path.basename(p) for p in captured['png_paths']] == [expected_name]
    assert os.path.exists(tmp_path / f'chr1-1000000-2000000.{disk_ext}')
    # --no-singularity must not wrap the command
    assert not captured['cmd'].startswith('singularity')


def test_cli_default_format_is_png(tmp_path):
    """Omitting -f gives PNG snapshots."""
    captured = {}
    _run_cli(
        ['igver', '-i', TEST_BAM, '-r', REGION, '-o', str(tmp_path), '--no-singularity'],
        captured,
    )
    assert 'snapshot chr1-1000000-2000000.png' in captured['batch']
    assert os.path.exists(tmp_path / 'chr1-1000000-2000000.png')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
