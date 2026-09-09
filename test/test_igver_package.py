#!/usr/bin/env python3
"""
Package-level test suite for igver.
Author: Samuel Ahuno
Purpose: verify the public API surface, CLI argument handling, batch script generation and
         singularity/container command construction without ever launching a real IGV/JVM.

Every test that reaches run_igv/load_screenshots patches igver.igver._run_until_stalled, which is
the single place where IGV is actually spawned.
"""

import pytest
import os
import sys
import subprocess
from unittest.mock import patch, Mock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_BAM = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_tumor.bam')
TEST_BAM2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_normal.bam')


def _fake_igv(cmd, png_paths, stall_timeout, debug=False):
    """Stand-in for _run_until_stalled: create the snapshots IGV would have written."""
    for png_path in png_paths:
        open(png_path, 'w').close()
    return True


# Test if package can be imported
def test_package_import():
    """Test that igver package can be imported."""
    import igver
    assert igver is not None


def test_package_version():
    """Test that package version is accessible."""
    try:
        import pkg_resources
        version = pkg_resources.get_distribution("igver").version
        assert version is not None
        assert isinstance(version, str)
        assert len(version) > 0
    except:
        # Version might not be available in dev mode
        pytest.skip("Version not available in development mode")


class TestAPIFunctions:
    """Test that all expected API functions are available."""

    def test_load_screenshots_exists(self):
        """Test that load_screenshots function exists."""
        import igver
        assert hasattr(igver, 'load_screenshots')
        assert callable(igver.load_screenshots)

    def test_create_batch_script_exists(self):
        """Test that create_batch_script function exists."""
        import igver
        assert hasattr(igver, 'create_batch_script')
        assert callable(igver.create_batch_script)

    def test_run_igv_exists(self):
        """Test that run_igv function exists."""
        import igver
        assert hasattr(igver, 'run_igv')
        assert callable(igver.run_igv)

    def test_function_signatures(self):
        """Test that functions have expected signatures."""
        import igver
        import inspect

        # Check load_screenshots parameters
        sig = inspect.signature(igver.load_screenshots)
        params = list(sig.parameters.keys())
        assert 'paths' in params
        assert 'regions' in params
        assert 'output_dir' in params
        assert 'genome' in params


class TestCLI:
    """Test command-line interface argument handling.

    These shell out on purpose but exit inside argparse, so IGV is never reached.
    """

    def test_cli_help(self):
        """`-h` prints usage and exits 0."""
        result = subprocess.run([sys.executable, '-m', 'igver.cli', '--help'],
                                capture_output=True, text=True, cwd=REPO_ROOT)
        assert result.returncode == 0
        assert 'usage' in result.stdout.lower()
        assert '--input' in result.stdout
        assert '--regions' in result.stdout

    def test_cli_missing_args(self):
        """Missing required arguments is an argparse error (exit 2), not a traceback."""
        result = subprocess.run([sys.executable, '-m', 'igver.cli'],
                                capture_output=True, text=True, cwd=REPO_ROOT)
        assert result.returncode == 2
        assert 'required' in result.stderr.lower()
        assert '--input' in result.stderr


class TestBatchScriptGeneration:
    """Test IGV batch script generation."""

    def test_batch_script_creation(self, tmp_path):
        """Multiple tracks are emitted as absolute `load` lines alongside genome/goto/snapshot."""
        import igver

        batch_file, png_paths = igver.create_batch_script(
            paths=[TEST_BAM, TEST_BAM2],
            regions=['chr1:1000-2000'],
            output_dir=str(tmp_path),
            genome='hg19',
        )

        assert os.path.exists(batch_file)
        content = open(batch_file).read()
        lines = content.splitlines()
        assert lines[0] == 'new'
        assert f'snapshotDirectory {os.path.abspath(str(tmp_path))}' in lines
        assert 'genome hg19' in lines
        # Paths are absolute so IGV resolves them the same way inside a container
        assert f'load {os.path.abspath(TEST_BAM)}' in lines
        assert f'load {os.path.abspath(TEST_BAM2)}' in lines
        assert 'goto chr1:1000-2000' in lines
        assert 'snapshot chr1-1000-2000.png' in lines
        assert lines[-1] == 'exit'
        assert [os.path.basename(p) for p in png_paths] == ['chr1-1000-2000.png']

    def test_batch_script_relative_paths_are_absolutised(self, tmp_path, monkeypatch):
        """A relative track path is written into the batch as an absolute path."""
        import igver

        rel_bam = 'rel_track.bam'
        (tmp_path / rel_bam).touch()
        monkeypatch.chdir(tmp_path)

        batch_file, _ = igver.create_batch_script(
            paths=[rel_bam],
            regions=['chr1:1000-2000'],
            output_dir=str(tmp_path),
            genome='hg19',
        )

        content = open(batch_file).read()
        assert f'load {os.path.join(str(tmp_path), rel_bam)}' in content.splitlines()
        assert f'load {rel_bam}' not in content.splitlines()


class TestCommandConstruction:
    """Test how the shell command handed to IGV is assembled."""

    def _batch(self, tmp_path):
        import igver
        return igver.create_batch_script(
            paths=[TEST_BAM],
            regions=['chr1:100-200'],
            output_dir=str(tmp_path),
            genome='hg19',
        )

    def test_load_screenshots_wraps_in_singularity(self, tmp_path):
        """load_screenshots(use_singularity=True) runs IGV through the named image."""
        import igver

        fake = Mock(side_effect=_fake_igv)
        with patch('igver.igver._run_until_stalled', fake):
            result = igver.load_screenshots(
                [TEST_BAM],
                ['chr1:100-200'],
                str(tmp_path),
                genome='hg19',
                use_singularity=True,
                singularity_image='test.sif',
                load_figures=False,
            )

        assert fake.call_count == 1
        cmd = fake.call_args[0][0]
        assert cmd.startswith('singularity run')
        assert 'test.sif' in cmd
        assert result == [str(tmp_path / 'chr1-100-200.png')]
        assert os.path.exists(result[0])

    def test_container_detection_skips_singularity(self, tmp_path):
        """Auto-detection (use_singularity=None) inside a container calls IGV directly."""
        import igver

        batch_file, png_paths = self._batch(tmp_path)
        fake = Mock(side_effect=_fake_igv)
        with patch('igver.igver.is_running_in_container', return_value=True), \
             patch('igver.igver._run_until_stalled', fake):
            igver.run_igv(batch_file, png_paths, use_singularity=None)

        cmd = fake.call_args[0][0]
        assert not cmd.startswith('singularity')
        assert 'igv.sh' in cmd

    def test_container_detection_uses_singularity_outside(self, tmp_path):
        """Auto-detection outside a container wraps IGV in singularity."""
        import igver

        batch_file, png_paths = self._batch(tmp_path)
        fake = Mock(side_effect=_fake_igv)
        with patch('igver.igver.is_running_in_container', return_value=False), \
             patch('igver.igver._run_until_stalled', fake):
            igver.run_igv(batch_file, png_paths, use_singularity=None,
                          singularity_image='auto.sif')

        cmd = fake.call_args[0][0]
        assert cmd.startswith('singularity run')
        assert 'auto.sif' in cmd
        assert 'igv.sh' in cmd


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
