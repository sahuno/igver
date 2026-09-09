"""
Regression tests for genome alias resolution.

Author: Samuel Ahuno
Date: 2026-09-09
Purpose: -g GRCh38 must resolve to the IGV genome id hg38. The loader previously
         read a nested `aliases:` key that genome_map.yaml does not have, so every
         alias silently fell through to IGV unchanged.
"""

import pytest

from igver.cli import _load_genome_mappings


@pytest.fixture(scope="module")
def genome_map():
    return _load_genome_mappings()


def test_mappings_are_not_empty(genome_map):
    """The shipped genome_map.yaml must actually load."""
    assert genome_map, "genome alias map loaded empty - aliases are not being resolved"


@pytest.mark.parametrize("alias,expected", [
    ("GRCh37", "hg19"),
    ("GRCh38", "hg38"),
    ("hg37", "hg19"),
    ("b37", "hg19"),
    ("GRCm38", "mm10"),
    ("GRCm39", "mm39"),
    ("Rnor_6.0", "rn6"),
    ("GRCz11", "danRer11"),
    ("hs1", "hs1"),
])
def test_known_aliases_resolve(genome_map, alias, expected):
    """Documented aliases in the README resolve to their IGV genome id."""
    assert genome_map.get(alias) == expected


@pytest.mark.parametrize("genome", ["hg38", "mm10", "my_custom.genome"])
def test_unknown_genome_passes_through(genome_map, genome):
    """A genome that is not an alias is handed to IGV unchanged (dict.get default)."""
    assert genome_map.get(genome, genome) == genome


def test_all_values_are_strings(genome_map):
    """Non-string entries are filtered out so they can never reach the IGV batch."""
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in genome_map.items())


def test_nested_aliases_layout_supported(tmp_path, monkeypatch):
    """A genome_map.yaml written with a nested `aliases:` block loads identically."""
    import igver.cli as cli

    yaml_file = tmp_path / "genome_map.yaml"
    yaml_file.write_text("aliases:\n  GRCh38: hg38\n  GRCm38: mm10\n")

    class _FakePath:
        def joinpath(self, _name):
            return yaml_file

    monkeypatch.setattr(cli.resources, "files", lambda _pkg: _FakePath())

    mapping = cli._load_genome_mappings()
    assert mapping == {"GRCh38": "hg38", "GRCm38": "mm10"}
