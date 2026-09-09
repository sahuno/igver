#!/usr/bin/env python3
"""
Tests for the .txt file input functionality in igver CLI.
Author: Samuel Ahuno
Purpose: cover _parse_input_file directly, and cover cli.main()'s handling of .txt track lists,
         direct paths, bad paths and the --no-singularity flag.

The CLI tests run main() in-process with igver.igver._run_until_stalled patched out, so no
Singularity container and no JVM is ever started.
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, Mock

# Add parent directory to path to import igver modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import igver.cli
from igver.cli import _parse_input_file

# Test data paths
TEST_DIR = Path(__file__).parent
TEST_BAM1 = TEST_DIR / "test_tumor.bam"
TEST_BAM2 = TEST_DIR / "test_normal.bam"
REGION = "8:32534767-32536767"


def _run_cli(argv):
    """
    Run igver.cli.main() in-process against a fake IGV.

    Returns:
        (mock, dict): the Mock standing in for _run_until_stalled, and a record with the
            shell command, the batch script text (read before run_igv deletes it) and the
            snapshot paths that were requested.
    """
    record = {'cmd': None, 'batch': None, 'png_paths': []}

    def fake_igv(cmd, png_paths, stall_timeout, debug=False):
        batch_path = cmd.split(' -b ')[1].split()[0]
        record['cmd'] = cmd
        record['batch'] = open(batch_path).read()
        record['png_paths'].extend(png_paths)
        for png_path in png_paths:
            open(png_path, 'w').close()
        return True

    fake = Mock(side_effect=fake_igv)
    with patch.object(sys, 'argv', ['igver'] + argv), \
         patch('igver.igver._run_until_stalled', fake):
        igver.cli.main()
    return fake, record


class TestInputFileParser:
    """Test the _parse_input_file function directly"""

    def test_parse_valid_input_file(self, tmp_path):
        """Test parsing a valid input file with multiple paths"""
        input_file = tmp_path / "tracks.txt"
        input_file.write_text(f"""# Test BAM files
{TEST_BAM1}

# Another BAM file
{TEST_BAM2}
""")

        paths = _parse_input_file(str(input_file))
        assert len(paths) == 2
        assert str(TEST_BAM1) in paths
        assert str(TEST_BAM2) in paths

    def test_parse_with_home_expansion(self, tmp_path):
        """Test that ~ is expanded to home directory"""
        input_file = tmp_path / "tracks.txt"
        input_file.write_text("~/test.bam\n")

        paths = _parse_input_file(str(input_file))
        assert len(paths) == 1
        assert paths[0] == os.path.expanduser("~/test.bam")

    def test_parse_empty_file(self, tmp_path):
        """Test that empty file raises error"""
        input_file = tmp_path / "empty.txt"
        input_file.write_text("")

        with pytest.raises(ValueError, match="No valid paths found"):
            _parse_input_file(str(input_file))

    def test_parse_comments_only(self, tmp_path):
        """Test that file with only comments raises error"""
        input_file = tmp_path / "comments.txt"
        input_file.write_text("# Just comments\n# Nothing else\n")

        with pytest.raises(ValueError, match="No valid paths found"):
            _parse_input_file(str(input_file))

    def test_parse_nonexistent_file(self):
        """Test that nonexistent file raises FileNotFoundError"""
        with pytest.raises(FileNotFoundError):
            _parse_input_file("/nonexistent/file.txt")


class TestCLIWithInputFile:
    """Test cli.main() with .txt file input (no IGV launched)."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.tmp_path = tmp_path
        self.output_dir = tmp_path / "output"
        self.output_dir.mkdir(exist_ok=True)

        self.input_file = tmp_path / "test_tracks.txt"
        self.input_file.write_text(f"{TEST_BAM1}\n{TEST_BAM2}\n")

        self.regions_file = tmp_path / "regions.txt"
        self.regions_file.write_text(REGION + "\n")

    def test_cli_with_txt_input_file(self, capsys):
        """A .txt track list loads every BAM it names as an absolute `load` line."""
        fake, record = _run_cli([
            "-i", str(self.input_file),
            "-r", str(self.regions_file),
            "-o", str(self.output_dir),
            "-g", "hg19",
            "--no-singularity",
        ])

        assert fake.call_count == 1
        out = capsys.readouterr().out
        assert "Loaded 2 track(s) from" in out
        batch_lines = record['batch'].splitlines()
        assert f"load {os.path.abspath(TEST_BAM1)}" in batch_lines
        assert f"load {os.path.abspath(TEST_BAM2)}" in batch_lines
        assert f"goto {REGION}" in batch_lines
        assert [os.path.basename(p) for p in record['png_paths']] == \
            ["8-32534767-32536767.png"]

    def test_cli_with_direct_paths(self, capsys):
        """Direct paths still work and do not print the track-list message."""
        fake, record = _run_cli([
            "-i", str(TEST_BAM1), str(TEST_BAM2),
            "-r", str(self.regions_file),
            "-o", str(self.output_dir),
            "-g", "hg19",
            "--no-singularity",
        ])

        assert fake.call_count == 1
        assert "Loaded" not in capsys.readouterr().out
        batch_lines = record['batch'].splitlines()
        assert f"load {os.path.abspath(TEST_BAM1)}" in batch_lines
        assert f"load {os.path.abspath(TEST_BAM2)}" in batch_lines

    def test_cli_with_invalid_path_in_file(self, tmp_path):
        """A missing track inside the .txt aborts before IGV is launched."""
        invalid_input = tmp_path / "invalid_tracks.txt"
        invalid_input.write_text("/nonexistent/file.bam\n")

        argv = ["igver", "-i", str(invalid_input), "-r", REGION,
                "-o", str(self.output_dir), "-g", "hg19", "--no-singularity"]
        fake = Mock(return_value=True)
        with patch.object(sys, 'argv', argv), \
             patch('igver.igver._run_until_stalled', fake), \
             pytest.raises(SystemExit) as excinfo:
            igver.cli.main()

        assert excinfo.value.code == 1
        fake.assert_not_called()  # aborted before IGV was launched

    def test_cli_mixed_txt_and_direct(self):
        """
        With more than one -i value the .txt is NOT expanded: cli.main() only treats the
        input as a track list when exactly one argument ending in .txt is given. Here the
        .txt itself is handed to IGV as a track.
        """
        fake, record = _run_cli([
            "-i", str(self.input_file), str(TEST_BAM1),
            "-r", REGION,
            "-o", str(self.output_dir),
            "-g", "hg19",
            "--no-singularity",
        ])

        assert fake.call_count == 1
        batch_lines = record['batch'].splitlines()
        assert f"load {os.path.abspath(self.input_file)}" in batch_lines
        assert f"load {os.path.abspath(TEST_BAM1)}" in batch_lines
        assert f"load {os.path.abspath(TEST_BAM2)}" not in batch_lines  # .txt was not expanded


class TestSingularityCompatibility:
    """Test how the --no-singularity flag and bind mounts shape the IGV command."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.tmp_path = tmp_path
        self.output_dir = tmp_path / "output"
        self.output_dir.mkdir(exist_ok=True)

        self.input_file = tmp_path / "tracks.txt"
        self.input_file.write_text(str(TEST_BAM1) + "\n")

    def test_no_singularity_flag_runs_igv_directly(self):
        """--no-singularity must not wrap the command in a (nested) singularity call."""
        _, record = _run_cli([
            "-i", str(self.input_file),
            "-r", REGION,
            "-o", str(self.output_dir),
            "-g", "hg19",
            "--no-singularity",
        ])

        assert not record['cmd'].startswith("singularity")
        assert "igv.sh" in record['cmd']

    def test_default_wraps_in_singularity(self):
        """Without the flag the command runs through the configured singularity image."""
        _, record = _run_cli([
            "-i", str(self.input_file),
            "-r", REGION,
            "-o", str(self.output_dir),
            "-g", "hg19",
            "--singularity-image", "my_test_image.sif",
        ])

        assert record['cmd'].startswith("singularity run")
        assert "my_test_image.sif" in record['cmd']

    def test_input_file_path_resolution(self, tmp_path):
        """Track dirs named in the .txt are bind-mounted into the container."""
        nested_dir = tmp_path / "data" / "bams"
        nested_dir.mkdir(parents=True)
        dummy_bam = nested_dir / "test.bam"
        dummy_bam.touch()
        (nested_dir / "test.bam.bai").touch()

        input_file = tmp_path / "inputs.txt"
        input_file.write_text(str(dummy_bam) + "\n")

        _, record = _run_cli([
            "-i", str(input_file),
            "-r", REGION,
            "-o", str(self.output_dir),
            "-g", "hg19",
            "--singularity-image", "my_test_image.sif",
        ])

        assert f"-B {nested_dir}" in record['cmd']
        assert f"-B {os.path.realpath(self.output_dir)}" in record['cmd']
        assert f"load {dummy_bam}" in record['batch'].splitlines()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
