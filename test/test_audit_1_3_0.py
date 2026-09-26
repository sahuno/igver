#!/usr/bin/env python3
"""
Acceptance tests for the 12 bugs found in the igver 1.2.3 audit (target release 1.3.0).

Author: Samuel Ahuno
Date: 2026-09-25
Purpose: one test class per audited bug (B1-B12, docs/plans/20260925_audit_bugfix_plan.md);
         written before the fixes, so every bug test fails on 1.2.3 and passes on 1.3.0.

Collection rule: only symbols that exist in 1.2.3 are imported at module top. Symbols added
by the fixes are imported inside the tests that use them, so a missing name fails that test
alone. No IGV or container is started: `_run_until_stalled` is patched with a fake.
"""

import gzip
import os
import random
import re
import shlex
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import igver.cli
from igver import igver as core
from igver.igver import _get_paths_and_regions, _parse_bed_file, _parse_region_file

REPO = Path(__file__).resolve().parent.parent
TEST_BAM = REPO / "test" / "test_tumor.bam"
REGION = "8:32534767-32536767"


# --------------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------------

def _gotos(content):
    """Return the arguments of every `goto` line in a list of batch lines."""
    return [line[len('goto '):] for line in content if line.startswith('goto')]


def _names(png_paths):
    return [os.path.basename(p) for p in png_paths]


def _write(path, text):
    path = Path(path)
    path.write_text(text)
    return str(path)


def _igv_dir_of(cmd):
    """Return the --igvDirectory argument of an IGV command line, or None."""
    m = re.search(r'--igvDirectory\s+(.+)$', cmd)
    return shlex.split(m.group(1))[0] if m else None


def _run_cli(argv, render=True, log_text=None):
    """
    Run igver.cli.main() in-process against a fake IGV.

    Parameters:
        argv (list of str): igver arguments (without the program name).
        render (bool): the fake writes every requested snapshot when True.
        log_text (str): if given, written to <igvDirectory>/igv0.log by the fake.

    Returns:
        (Mock, dict): the fake and a record with every command, batch text, and the
            prefs.properties text seen in each run's --igvDirectory.
    """
    record = {'cmds': [], 'batches': [], 'prefs': [], 'igv_dirs': [], 'png_paths': []}

    def fake_igv(cmd, png_paths, stall_timeout, debug=False):
        batch_path = shlex.split(cmd.split(' -b ', 1)[1])[0]
        record['cmds'].append(cmd)
        record['batches'].append(open(batch_path).read())
        record['png_paths'].extend(png_paths)
        igv_dir = _igv_dir_of(cmd)
        record['igv_dirs'].append(igv_dir)
        prefs = os.path.join(igv_dir, 'prefs.properties') if igv_dir else None
        record['prefs'].append(open(prefs).read() if prefs and os.path.exists(prefs) else None)
        if log_text is not None and igv_dir and os.path.isdir(igv_dir):
            _write(os.path.join(igv_dir, 'igv0.log'), log_text)
        if render:
            for png_path in png_paths:
                open(png_path, 'w').close()
        return render

    fake = Mock(side_effect=fake_igv)
    with patch.object(sys, 'argv', ['igver'] + argv), \
         patch('igver.igver._run_until_stalled', fake):
        igver.cli.main()
    return fake, record


def _cli_exits(argv):
    """Run the CLI expecting exit 1 before IGV starts. Returns the fake (asserted uncalled)."""
    fake = Mock(return_value=True)
    with patch.object(sys, 'argv', ['igver'] + argv), \
         patch('igver.igver._run_until_stalled', fake), \
         pytest.raises(SystemExit) as excinfo:
        igver.cli.main()
    assert excinfo.value.code == 1
    fake.assert_not_called()
    return fake


def _bam_with_index(tmp_path, index_suffix):
    """Make an empty `x.bam` plus an index named with `index_suffix` ('' = no index)."""
    bam = tmp_path / "x.bam"
    bam.touch()
    if index_suffix == 'stem.bai':
        (tmp_path / "x.bai").touch()
    elif index_suffix:
        (tmp_path / f"x.bam{index_suffix}").touch()
    return str(bam)


# --------------------------------------------------------------------------------------------
# B1 - screenshots depend on the user's ~/igv; B11 - -j processes share ~/igv
# --------------------------------------------------------------------------------------------

class TestB1IsolatedIgvDirectory:

    def test_template_is_packaged_and_loadable(self):
        from igver.igver import read_prefs_template
        text = read_prefs_template()
        keys = dict(line.split('=', 1) for line in text.splitlines()
                    if line.strip() and not line.startswith('#'))
        assert keys['IGV.Bounds'] == '0,0,1150,800'
        assert keys['PORT_ENABLED'] == 'false'
        assert keys['SAM.DOWNSAMPLE_READS'] == 'true'
        assert keys['SAM.SHOW_SOFT_CLIPPED'] == 'false'

    def test_template_in_clean_venv_install(self, tmp_path):
        """`pip install .` (not editable) ships the template and it loads from site-packages.

        The venv has no system site-packages, so the editable install of this checkout (a .pth
        finder in the base env) cannot shadow it. Runtime deps (Pillow, matplotlib, PyYAML) come
        from the base env via PYTHONPATH, where .pth files are not executed.
        """
        import site
        venv = tmp_path / "venv"
        subprocess.run([sys.executable, '-m', 'venv', str(venv)], check=True)
        py = str(venv / 'bin' / 'python')
        subprocess.run([py, '-m', 'pip', 'install', '-q', '--no-deps', str(REPO)],
                       check=True, cwd=str(tmp_path))
        deps = site.getsitepackages() + [site.getusersitepackages()]
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(deps))
        out = subprocess.run(
            [py, '-c', 'import igver, igver.igver as m; print(igver.__file__); '
                       'print(len(m.read_prefs_template()))'],
            check=True, cwd=str(tmp_path), capture_output=True, text=True, env=env).stdout.split()
        assert out[0].startswith(str(venv)), f"imported from {out[0]}, not the venv"
        assert int(out[1]) > 0

    def test_command_uses_run_scoped_igv_directory(self, tmp_path):
        _, rec = _run_cli(['-i', str(TEST_BAM), '-r', REGION, '-o', str(tmp_path / 'o'),
                           '-g', 'hg19', '--no-singularity'])
        igv_dir = rec['igv_dirs'][0]
        assert igv_dir is not None
        assert os.path.basename(igv_dir).startswith('igver_igv_')
        assert not igv_dir.startswith('/opt/'), "the read-only install dir is not an IGV dir"
        assert '--igvDirectory /opt/IGV_2.19.8' not in rec['cmds'][0]

    def test_run_dir_gets_template_prefs_and_default_genome(self, tmp_path):
        _, rec = _run_cli(['-i', str(TEST_BAM), '-r', REGION, '-o', str(tmp_path / 'o'),
                           '-g', 'hg19', '--no-singularity'])
        prefs = rec['prefs'][0]
        assert prefs is not None, "no prefs.properties in the run dir when IGV started"
        assert 'IGV.Bounds=0,0,1150,800' in prefs
        assert 'PORT_ENABLED=false' in prefs
        assert 'DEFAULT_GENOME_KEY=hg19' in prefs

    def test_run_dir_removed_on_success(self, tmp_path):
        _, rec = _run_cli(['-i', str(TEST_BAM), '-r', REGION, '-o', str(tmp_path / 'o'),
                           '-g', 'hg19', '--no-singularity'])
        igv_dir = rec['igv_dirs'][0]
        assert igv_dir and os.path.basename(igv_dir).startswith('igver_igv_')
        assert rec['prefs'][0] is not None, "run dir did not exist while IGV ran"
        assert not os.path.exists(igv_dir)

    def test_run_dir_kept_on_failure_with_log_excerpt(self, tmp_path, capsys):
        log = ("INFO [x] [Main] IGV Directory: somewhere\n"
               "SEVERE [x] [Foo] something broke badly\n"
               "INFO [x] fine\n")
        fake = None
        with pytest.raises(SystemExit) as excinfo:
            fake, rec = _run_cli(['-i', str(TEST_BAM), '-r', REGION, '-o', str(tmp_path / 'o'),
                                  '-g', 'hg19', '--no-singularity', '--stall-timeout', '5'],
                                 render=False, log_text=log)
        assert excinfo.value.code == 1
        err = capsys.readouterr().err
        assert 'something broke badly' in err
        dirs = re.findall(r'(\S*igver_igv_\S*?)(?=[\s,;:)]|$)', err)
        assert dirs and any(os.path.isdir(d.rstrip('.')) for d in dirs), \
            f"failure message must name an existing kept run dir:\n{err}"

    def test_igv_prefs_lines_appended(self, tmp_path):
        prefs = _write(tmp_path / 'my.prefs', '# comment\nSAM.SHOW_SOFT_CLIPPED=true\n\n')
        _, rec = _run_cli(['-i', str(TEST_BAM), '-r', REGION, '-o', str(tmp_path / 'o'),
                           '-g', 'hg19', '--no-singularity', '--igv-prefs', prefs])
        text = rec['prefs'][0]
        assert text is not None
        # the user value comes after (and therefore overrides) the template value
        assert text.rindex('SAM.SHOW_SOFT_CLIPPED=true') > text.index('SAM.SHOW_SOFT_CLIPPED=false')

    def test_igv_prefs_parser_positive(self, tmp_path):
        from igver.igver import parse_igv_prefs
        path = _write(tmp_path / 'p', '# c\nA=1\n  B.C = x y \n\n')
        assert parse_igv_prefs(path) == ['A=1', 'B.C=x y']

    def test_igv_prefs_parser_empty_file(self, tmp_path):
        from igver.igver import parse_igv_prefs
        assert parse_igv_prefs(_write(tmp_path / 'p', '')) == []

    @pytest.mark.parametrize('bad', ['JUSTAKEY', '=value', 'colorBy BASE_MODIFICATION'])
    def test_igv_prefs_parser_rejects_malformed(self, tmp_path, bad):
        from igver.igver import parse_igv_prefs
        path = _write(tmp_path / 'p', f'A=1\n{bad}\n')
        with pytest.raises(ValueError, match=r':2'):
            parse_igv_prefs(path)

    def test_malformed_igv_prefs_exits_before_igv(self, tmp_path):
        prefs = _write(tmp_path / 'bad.prefs', 'NOT A PREF LINE\n')
        _cli_exits(['-i', str(TEST_BAM), '-r', REGION, '-o', str(tmp_path / 'o'),
                    '-g', 'hg19', '--no-singularity', '--igv-prefs', prefs])

    def test_missing_igv_prefs_exits_before_igv(self, tmp_path):
        _cli_exits(['-i', str(TEST_BAM), '-r', REGION, '-o', str(tmp_path / 'o'),
                    '-g', 'hg19', '--no-singularity', '--igv-prefs', str(tmp_path / 'nope')])


class TestB11ParallelJobsIsolated:

    def test_each_job_gets_its_own_igv_directory(self, tmp_path):
        _, rec = _run_cli(['-i', str(TEST_BAM), '-r', 'chr1:1-100', 'chr2:1-100',
                           '-o', str(tmp_path / 'o'), '-g', 'hg19', '--no-singularity', '-j', '2'])
        assert len(rec['igv_dirs']) == 2
        assert None not in rec['igv_dirs']
        assert len(set(rec['igv_dirs'])) == 2

    def test_port_disabled_for_every_job(self, tmp_path):
        _, rec = _run_cli(['-i', str(TEST_BAM), '-r', 'chr1:1-100', 'chr2:1-100',
                           '-o', str(tmp_path / 'o'), '-g', 'hg19', '--no-singularity', '-j', '2'])
        assert all(p is not None and 'PORT_ENABLED=false' in p for p in rec['prefs'])


# --------------------------------------------------------------------------------------------
# B2 - text region files
# --------------------------------------------------------------------------------------------

class TestB2RegionFileGrammar:

    def _parse(self, tmp_path, text):
        path = _write(tmp_path / 'regions.txt', text)
        return _parse_region_file(path, str(tmp_path))

    def test_locus_id_tag_with_plus_stays_a_tag(self, tmp_path):
        png, content = self._parse(tmp_path, 'chr1:1-2 chr1:1-2.L1.1.+\n')
        assert _gotos(content) == ['chr1:1-2']
        assert _names(png) == ['chr1-1-2.chr1_1-2.L1.1.+.png']

    def test_multi_word_tag_preserved(self, tmp_path):
        png, content = self._parse(tmp_path, 'chr1:1-2\tmy tag here\n')
        assert _gotos(content) == ['chr1:1-2']
        assert _names(png) == ['chr1-1-2.my_tag_here.png']

    def test_bed_like_line_in_txt(self, tmp_path, capsys):
        png, content = self._parse(tmp_path, 'chr1 100 200 regionA\n')
        assert _gotos(content) == ['chr1:101-200']
        assert _names(png) == ['chr1-100-200.regionA.png']
        assert 'BED-like' in capsys.readouterr().out

    def test_bed_like_tab_line_in_txt(self, tmp_path):
        png, content = self._parse(tmp_path, 'chr1\t100\t200\tx\n')
        assert _gotos(content) == ['chr1:101-200']
        assert _names(png) == ['chr1-100-200.x.png']

    def test_gene_name_alone_errors_with_line_number(self, tmp_path):
        path = _write(tmp_path / 'regions.txt', '# header\nchr1:1-2\nTP53\n')
        with pytest.raises(ValueError, match=re.escape(f'{path}:3')):
            _parse_region_file(path, str(tmp_path))

    def test_reversed_coordinates_error(self, tmp_path):
        path = _write(tmp_path / 'regions.txt', 'chr1:200-100\n')
        with pytest.raises(ValueError, match=re.escape(f'{path}:1')):
            _parse_region_file(path, str(tmp_path))

    def test_comma_coordinates(self, tmp_path):
        png, content = self._parse(tmp_path, 'chr1:1,000-2,000 x\n')
        assert _gotos(content) == ['chr1:1000-2000']
        assert _names(png) == ['chr1-1000-2000.x.png']

    def test_legacy_sv_lines_still_work(self, tmp_path):
        text = (REPO / 'test' / 'regions.txt').read_text()
        png, content = self._parse(tmp_path, text)
        assert _gotos(content) == [
            '8:32534767-32536767',
            '8:32534767-32536767 19:11137898-11139898',
            '19:16780041-16782041 19:17553189-17555189',
            '19:12874447-12876447 19:13500000-13501000 19:14461465-14463465',
        ]
        assert _names(png) == [
            '8-32534767-32536767.region_of_interest.png',
            '8-32534767-32536767.19-11137898-11139898.translocation.png',
            '19-16780041-16782041.19-17553189-17555189.inversion.png',
            '19-12874447-12876447.19-13500000-13501000.19-14461465-14463465.duplication.png',
        ]

    def test_tag_with_colon_and_dash_in_later_position(self, tmp_path):
        png, content = self._parse(tmp_path, 'chr1:1-2 del ref:3-4\n')
        assert _gotos(content) == ['chr1:1-2']
        assert _names(png) == ['chr1-1-2.del_ref_3-4.png']

    def test_hla_alt_contig_is_one_locus(self, tmp_path):
        from igver.igver import parse_locus
        assert parse_locus('HLA-A*01:01:01:01:1-100') == ('HLA-A*01:01:01:01', 1, 100)
        png, content = self._parse(tmp_path, 'HLA-A*01:01:01:01:1-100\n')
        assert _gotos(content) == ['HLA-A*01:01:01:01:1-100']

    def test_unplaced_contig(self, tmp_path):
        png, content = self._parse(tmp_path, 'chrUn_JH584304:1-100\n')
        assert _gotos(content) == ['chrUn_JH584304:1-100']
        assert _names(png) == ['chrUn_JH584304-1-100.png']

    def test_empty_tag_whitespace_crlf_and_tabs(self, tmp_path):
        png, content = self._parse(tmp_path, 'chr1:1-2\r\n   \t \r\n\tchr2:3-4\t\tt\r\n')
        assert _gotos(content) == ['chr1:1-2', 'chr2:3-4']
        assert _names(png) == ['chr1-1-2.png', 'chr2-3-4.t.png']

    def test_no_empty_goto_ever_fuzz(self, tmp_path):
        """1,000 random lines: each raises ValueError naming file:line, or yields real loci."""
        from igver.igver import parse_locus
        rng = random.Random(42)
        alphabet = 'chr1XY:-,.+|_ \t0123456789ab'
        path = str(tmp_path / 'fuzz.txt')
        for _ in range(1000):
            n = rng.randint(0, 30)
            line = ''.join(rng.choice(alphabet) for _ in range(n))
            if rng.random() < 0.3:
                line = f'chr{rng.randint(1, 22)}:{rng.randint(1, 500)}-{rng.randint(1, 900)} ' + line
            _write(path, line + '\n')
            try:
                _, content = _parse_region_file(path, str(tmp_path))
            except ValueError as e:
                assert f'{path}:1' in str(e), f'no line number for {line!r}: {e}'
                continue
            for arg in _gotos(content):
                assert arg.strip(), f'empty goto from {line!r}'
                for token in arg.split():
                    assert parse_locus(token), f'bad locus {token!r} from {line!r}'


# --------------------------------------------------------------------------------------------
# B3 - missing index pre-flight
# --------------------------------------------------------------------------------------------

class TestB3IndexPreflight:

    @pytest.mark.parametrize('suffix', ['.bai', 'stem.bai', '.csi'])
    def test_bam_index_names_accepted(self, tmp_path, suffix):
        from igver.igver import find_missing_indexes
        assert find_missing_indexes([_bam_with_index(tmp_path, suffix)]) == []

    def test_bam_without_index(self, tmp_path):
        from igver.igver import find_missing_indexes
        bam = _bam_with_index(tmp_path, '')
        problems = find_missing_indexes([bam])
        assert len(problems) == 1
        assert f'{bam}.bai' in problems[0] and 'samtools index' in problems[0]

    @pytest.mark.parametrize('index', ['x.cram.crai', 'x.crai'])
    def test_cram_index_names_accepted(self, tmp_path, index):
        from igver.igver import find_missing_indexes
        (tmp_path / 'x.cram').touch()
        (tmp_path / index).touch()
        assert find_missing_indexes([str(tmp_path / 'x.cram')]) == []

    def test_cram_without_index(self, tmp_path):
        from igver.igver import find_missing_indexes
        (tmp_path / 'x.cram').touch()
        problems = find_missing_indexes([str(tmp_path / 'x.cram')])
        assert len(problems) == 1 and 'crai' in problems[0]

    @pytest.mark.parametrize('name,index', [('v.vcf.gz', 'v.vcf.gz.tbi'), ('v.vcf.gz', 'v.vcf.gz.csi'),
                                            ('v.bcf', 'v.bcf.csi')])
    def test_vcf_index_names_accepted(self, tmp_path, name, index):
        from igver.igver import find_missing_indexes
        (tmp_path / name).touch()
        (tmp_path / index).touch()
        assert find_missing_indexes([str(tmp_path / name)]) == []

    def test_vcf_without_index(self, tmp_path):
        from igver.igver import find_missing_indexes
        (tmp_path / 'v.vcf.gz').touch()
        problems = find_missing_indexes([str(tmp_path / 'v.vcf.gz')])
        assert len(problems) == 1 and 'tabix' in problems[0]

    def test_symlink_with_index_only_beside_target(self, tmp_path):
        from igver.igver import find_missing_indexes
        real = tmp_path / 'real'
        real.mkdir()
        target = _bam_with_index(real, '.bai')
        link = tmp_path / 'link.bam'
        link.symlink_to(target)
        problems = find_missing_indexes([str(link)])
        assert len(problems) == 1
        assert f'{target}.bai' in problems[0], problems[0]
        assert 'ln -s' in problems[0]

    def test_urls_and_non_indexed_types_skipped(self, tmp_path):
        from igver.igver import find_missing_indexes
        bed = tmp_path / 'a.hg19.bed'
        bed.touch()
        assert find_missing_indexes(['https://example.org/x.bam', 's3://b/x.cram', str(bed)]) == []

    def test_stall_failure_names_last_resource_despite_unrelated_severe(self, tmp_path, capsys):
        # IGV logs nothing for a 404 track URL; an unrelated SEVERE line must not hide the last line
        log = ("SEVERE [x] [DefaultExceptionHandler] java.lang.ClassFormatError: XSystemTrayPeer\n"
               "INFO [x] [TrackLoader] Loading resource:  https://example.org/missing.bam\n"
               "INFO [x] [ShutdownThread] Shutting down\n")
        with pytest.raises(SystemExit):
            _run_cli(['-i', str(TEST_BAM), '-r', REGION, '-o', str(tmp_path / 'o'),
                      '-g', 'hg19', '--no-singularity'], render=False, log_text=log)
        err = capsys.readouterr().err
        assert 'ClassFormatError' in err and 'Loading resource:  https://example.org/missing.bam' in err

    def test_cli_exits_before_igv_on_missing_index(self, tmp_path, capsys):
        bam = _bam_with_index(tmp_path, '')
        _cli_exits(['-i', bam, '-r', REGION, '-o', str(tmp_path / 'o'), '-g', 'hg19',
                    '--no-singularity'])
        assert f'{bam}.bai' in capsys.readouterr().err

    def test_stall_failure_prints_igv_log(self, tmp_path, capsys):
        log = "SEVERE [x] [AlignmentTrack] Error loading the thing\n"
        with pytest.raises(SystemExit):
            _run_cli(['-i', str(TEST_BAM), '-r', REGION, '-o', str(tmp_path / 'o'),
                      '-g', 'hg19', '--no-singularity'], render=False, log_text=log)
        assert 'Error loading the thing' in capsys.readouterr().err


# --------------------------------------------------------------------------------------------
# B4 - filename sanitiser
# --------------------------------------------------------------------------------------------

class TestB4Sanitiser:

    @pytest.mark.parametrize('raw,clean', [
        ('my region', 'my_region'),
        ('LINE/L1', 'LINE_L1'),
        ('chr1:1-2.L1|3.-', 'chr1_1-2.L1_3.-'),
        ('.hidden', 'hidden'),
        ('a  //  b', 'a_b'),
        ('keep.these_+=,-', 'keep.these_+=,-'),
        ('L1Mdé_ü', 'L1Md_'),
    ])
    def test_sanitise(self, raw, clean):
        from igver.igver import sanitize_name
        assert sanitize_name(raw) == clean

    def test_unicode_becomes_ascii(self):
        from igver.igver import sanitize_name
        out = sanitize_name('αβ-中文-name')
        assert out.isascii() and 'name' in out

    def test_idempotent(self):
        from igver.igver import sanitize_name
        rng = random.Random(42)
        chars = 'aZ09._+=,- /|:*?"<>\\é中\t'
        for _ in range(500):
            s = ''.join(rng.choice(chars) for _ in range(rng.randint(0, 25)))
            once = sanitize_name(s)
            assert sanitize_name(once) == once

    def test_bed_name_with_space_and_slash(self, tmp_path):
        bed = _write(tmp_path / 'r.hg19.bed', 'chr1\t100\t200\tmy region\nchr1\t300\t400\tLINE/L1\n')
        png, content = _parse_bed_file(bed, str(tmp_path))
        assert _names(png) == ['chr1-100-200.my_region.png', 'chr1-300-400.LINE_L1.png']
        snaps = [line for line in content if line.startswith('snapshot')]
        assert snaps == ['snapshot chr1-100-200.my_region.png', 'snapshot chr1-300-400.LINE_L1.png']

    @pytest.mark.parametrize('name,expected', [('a|b', 'a_b'), ('a:b', 'a_b'), ('.lead', 'lead'),
                                               ('_.lead', 'lead')])
    def test_bed_name_special_characters(self, tmp_path, name, expected):
        bed = _write(tmp_path / 'r.hg19.bed', f'chr1\t100\t200\t{name}\n')
        png, _ = _parse_bed_file(bed, str(tmp_path))
        assert _names(png) == [f'chr1-100-200.{expected}.png']

    def test_long_name_truncated(self, tmp_path):
        bed = _write(tmp_path / 'r.hg19.bed', 'chr1\t100\t200\t' + 'x' * 300 + '\n')
        png, _ = _parse_bed_file(bed, str(tmp_path))
        base = _names(png)[0]
        assert len(base.encode()) <= 200
        assert base.startswith('chr1-100-200.') and base.endswith('.png')

    def test_unicode_bed_name(self, tmp_path):
        bed = tmp_path / 'r.hg19.bed'
        bed.write_text('chr1\t100\t200\trégion\n', encoding='utf-8')
        png, _ = _parse_bed_file(str(bed), str(tmp_path))
        assert _names(png)[0].isascii()

    def test_paths_with_spaces_quoted_in_batch_and_binds(self, tmp_path):
        spaced = tmp_path / 'with space'
        spaced.mkdir()
        bam = _bam_with_index(spaced, '.bai')
        _, rec = _run_cli(['-i', bam, '-r', REGION, '-o', str(tmp_path / 'out dir'), '-g', 'hg19',
                           '--singularity-image', 'img.sif'])
        lines = rec['batches'][0].splitlines()
        assert f'load "{bam}"' in lines
        assert f'snapshotDirectory "{tmp_path}/out dir"' in lines
        assert f"-B '{spaced}'" in rec['cmds'][0]

    def test_tag_argument_sanitised(self, tmp_path):
        png, _ = _get_paths_and_regions(['chr1:1-2'], output_dir=str(tmp_path), tag='a b/c')
        assert _names(png) == ['chr1-1-2.a_b_c.png']


# --------------------------------------------------------------------------------------------
# B5 - region argument validation
# --------------------------------------------------------------------------------------------

class TestB5RegionArguments:

    @pytest.mark.parametrize('arg', ['regins.bed', 'typo.txt', 'TYPO.BED', 'dir/regions',
                                     'x.bed.gz', 'x.tsv', 'x.csv'])
    def test_missing_region_file_errors(self, tmp_path, arg):
        with pytest.raises(FileNotFoundError, match='region file not found'):
            _get_paths_and_regions([str(tmp_path / arg) if '/' in arg else arg],
                                   output_dir=str(tmp_path))

    def test_gene_name_accepted(self, tmp_path):
        png, content = _get_paths_and_regions(['TP53'], output_dir=str(tmp_path))
        assert _gotos(content) == ['TP53'] and _names(png) == ['TP53.png']

    def test_split_view_string_accepted(self, tmp_path):
        png, content = _get_paths_and_regions(['chr1:1-100 chr2:5-10'], output_dir=str(tmp_path))
        assert _gotos(content) == ['chr1:1-100 chr2:5-10']
        assert _names(png) == ['chr1-1-100.chr2-5-10.png']

    def test_reversed_region_string_rejected(self, tmp_path):
        with pytest.raises(ValueError):
            _get_paths_and_regions(['chr1:100-1'], output_dir=str(tmp_path))

    def test_multi_token_non_locus_rejected(self, tmp_path):
        with pytest.raises(ValueError):
            _get_paths_and_regions(['TP53 BRCA1'], output_dir=str(tmp_path))

    def test_cli_typo_exits_before_igv(self, tmp_path, capsys, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _cli_exits(['-i', str(TEST_BAM), '-r', 'typo.bed', '-o', str(tmp_path / 'o'),
                    '-g', 'hg19', '--no-singularity'])
        assert 'region file not found' in capsys.readouterr().err


# --------------------------------------------------------------------------------------------
# B6 - duplicate snapshot names
# --------------------------------------------------------------------------------------------

class TestB6Duplicates:

    def test_duplicate_bed_line_dropped_with_warning(self, tmp_path, capsys):
        bed = _write(tmp_path / 'd.hg19.bed', 'chr1\t100\t200\ta\nchr1\t100\t200\ta\nchr2\t1\t9\tb\n')
        png, content = _get_paths_and_regions([bed], output_dir=str(tmp_path))
        assert _names(png) == ['chr1-100-200.a.png', 'chr2-1-9.b.png']
        assert len(_gotos(content)) == 2
        assert 'duplicate' in capsys.readouterr().out.lower()

    def test_duplicates_across_files(self, tmp_path):
        a = _write(tmp_path / 'a.hg19.bed', 'chr1\t100\t200\tx\n')
        b = _write(tmp_path / 'b.hg19.bed', 'chr1\t100\t200\tx\nchr3\t5\t6\n')
        png, content = _get_paths_and_regions([a, b], output_dir=str(tmp_path))
        assert _names(png) == ['chr1-100-200.x.png', 'chr3-5-6.png']
        assert len(_gotos(content)) == 2

    def test_batch_has_no_duplicate_snapshots(self, tmp_path):
        bed = _write(tmp_path / 'd.hg19.bed', 'chr1\t100\t200\ta\nchr1\t100\t200\ta\n')
        batch, png = core.create_batch_script([str(TEST_BAM)], [bed], str(tmp_path))
        snaps = [line for line in open(batch).read().splitlines()
                 if line.startswith('snapshot ') and 'igver_' not in line]  # not the 1.4.0 stability capture
        assert len(snaps) == len(set(snaps)) == 1 and len(png) == 1

    def test_same_filename_different_locus_raises(self, tmp_path):
        # a BED record's filename keeps its 0-based start, so these two collide on the name
        txt = _write(tmp_path / 'a.txt', 'chr1:100-200 x\n')
        bed = _write(tmp_path / 'b.hg19.bed', 'chr1\t100\t200\tx\n')
        with pytest.raises(ValueError, match='chr1-100-200.x.png'):
            _get_paths_and_regions([txt, bed], output_dir=str(tmp_path))


# --------------------------------------------------------------------------------------------
# B7 - .txt track lists anywhere in -i
# --------------------------------------------------------------------------------------------

class TestB7TrackLists:

    def test_list_then_extra_track(self, tmp_path):
        from igver.cli import expand_track_lists
        lst = _write(tmp_path / 'list.txt', f'{TEST_BAM}\n# c\n\n{REPO}/test/test_normal.bam\n')
        assert expand_track_lists([lst, 'extra.bam']) == \
            [str(TEST_BAM), f'{REPO}/test/test_normal.bam', 'extra.bam']

    def test_two_lists_preserve_order(self, tmp_path):
        from igver.cli import expand_track_lists
        a = _write(tmp_path / 'a.TXT', 'one.bam\n')
        b = _write(tmp_path / 'b.txt', 'two.bam\nthree.bw\n')
        assert expand_track_lists(['zero.bam', a, b]) == ['zero.bam', 'one.bam', 'two.bam', 'three.bw']

    def test_missing_list_errors(self, tmp_path):
        from igver.cli import expand_track_lists
        with pytest.raises(FileNotFoundError):
            expand_track_lists([str(tmp_path / 'missing.txt'), 'x.bam'])

    def test_cli_mixed_list_and_track(self, tmp_path):
        lst = _write(tmp_path / 'tracks.txt', f'{TEST_BAM}\n')
        bed = _write(tmp_path / 'genes.hg19.bed', 'chr1\t1\t2\tg\n')
        _, rec = _run_cli(['-i', lst, bed, '-r', REGION, '-o', str(tmp_path / 'o'),
                           '-g', 'hg19', '--no-singularity'])
        loads = [line for line in rec['batches'][0].splitlines() if line.startswith('load')]
        assert loads == [f'load {TEST_BAM}', f'load {bed}']


# --------------------------------------------------------------------------------------------
# B8 - local FASTA / genome file passed to -g
# --------------------------------------------------------------------------------------------

class TestB8GenomeFile:

    def test_relative_fasta_absolute_in_batch_and_bound(self, tmp_path, monkeypatch):
        ref = tmp_path / 'ref'
        ref.mkdir()
        (ref / 'g.fa').write_text('>1\nACGT\n')
        (ref / 'g.fa.fai').write_text('1\t4\t3\t4\t5\n')
        monkeypatch.chdir(ref)
        _, rec = _run_cli(['-i', str(TEST_BAM), '-r', REGION, '-o', str(tmp_path / 'o'),
                           '-g', 'g.fa', '--singularity-image', 'img.sif'])
        assert f'genome {ref}/g.fa' in rec['batches'][0].splitlines()
        assert f'-B {ref}' in rec['cmds'][0]

    def test_symlinked_fasta_binds_realpath_dir(self, tmp_path):
        real = tmp_path / 'db'
        real.mkdir()
        (real / 'g.fa').write_text('>1\nACGT\n')
        (real / 'g.fa.fai').write_text('1\t4\t3\t4\t5\n')
        links = tmp_path / 'links'
        links.mkdir()
        (links / 'g.fa').symlink_to(real / 'g.fa')
        (links / 'g.fa.fai').symlink_to(real / 'g.fa.fai')
        _, rec = _run_cli(['-i', str(TEST_BAM), '-r', REGION, '-o', str(tmp_path / 'o'),
                           '-g', str(links / 'g.fa'), '--singularity-image', 'img.sif'])
        assert f'-B {links}' in rec['cmds'][0] and f'-B {real}' in rec['cmds'][0]

    def test_fasta_without_fai_exits(self, tmp_path, capsys):
        (tmp_path / 'g.fa').write_text('>1\nACGT\n')
        _cli_exits(['-i', str(TEST_BAM), '-r', REGION, '-o', str(tmp_path / 'o'),
                    '-g', str(tmp_path / 'g.fa'), '--no-singularity'])
        assert 'g.fa.fai' in capsys.readouterr().err

    def test_gz_fasta_needs_gzi(self, tmp_path, capsys):
        (tmp_path / 'g.fa.gz').write_bytes(b'')
        (tmp_path / 'g.fa.gz.fai').touch()
        _cli_exits(['-i', str(TEST_BAM), '-r', REGION, '-o', str(tmp_path / 'o'),
                    '-g', str(tmp_path / 'g.fa.gz'), '--no-singularity'])
        assert '.gzi' in capsys.readouterr().err

    def test_alias_still_maps(self, tmp_path):
        _, rec = _run_cli(['-i', str(TEST_BAM), '-r', REGION, '-o', str(tmp_path / 'o'),
                           '-g', 'GRCh38', '--no-singularity'])
        assert 'genome hg38' in rec['batches'][0].splitlines()


# --------------------------------------------------------------------------------------------
# B9 - BED parsing robustness
# --------------------------------------------------------------------------------------------

class TestB9BedParsing:

    def test_space_separated_bed_parses_with_warning(self, tmp_path, capsys):
        bed = _write(tmp_path / 's.hg19.bed', 'chr1 100 200 a\nchr2  300 400\n')
        png, content = _parse_bed_file(bed, str(tmp_path))
        assert _names(png) == ['chr1-100-200.a.png', 'chr2-300-400.png']
        out = capsys.readouterr().out
        assert out.count('[WARNING]') == 1 and 'whitespace' in out

    def test_non_integer_coordinate_errors_with_line(self, tmp_path):
        bed = _write(tmp_path / 'b.hg19.bed', '#chr\tstart\tend\nchr1\tabc\t200\n')
        with pytest.raises(ValueError, match=re.escape(f'{bed}:2')):
            _parse_bed_file(bed, str(tmp_path))

    def test_unparseable_line_errors(self, tmp_path):
        bed = _write(tmp_path / 'b.hg19.bed', 'chr1\t1\t2\nincomplete line\n')
        with pytest.raises(ValueError, match=re.escape(f'{bed}:2')):
            _parse_bed_file(bed, str(tmp_path))

    def test_header_lines_skipped(self, tmp_path):
        bed = _write(tmp_path / 'h.hg19.bed',
                     'track name=x\nbrowser position chr1:1-2\n#chr\tstart\tend\tname\nchr1\t5\t9\tn\n')
        png, _ = _parse_bed_file(bed, str(tmp_path))
        assert _names(png) == ['chr1-5-9.n.png']

    def test_uppercase_extension(self, tmp_path):
        bed = _write(tmp_path / 'r.hg19.BED', 'chr1\t5\t9\tn\n')
        png, content = _get_paths_and_regions([bed], output_dir=str(tmp_path))
        assert _names(png) == ['chr1-5-9.n.png'] and _gotos(content) == ['chr1:6-9']

    def test_bed_gz(self, tmp_path):
        path = tmp_path / 'r.hg19.bed.gz'
        with gzip.open(path, 'wt') as f:
            f.write('chr1\t5\t9\tn\n')
        png, content = _get_paths_and_regions([str(path)], output_dir=str(tmp_path))
        assert _names(png) == ['chr1-5-9.n.png'] and _gotos(content) == ['chr1:6-9']

    def test_empty_bed_errors(self, tmp_path):
        bed = _write(tmp_path / 'e.hg19.bed', '#chr\tstart\tend\n')
        with pytest.raises(ValueError, match=re.escape(bed)):
            _parse_bed_file(bed, str(tmp_path))


# --------------------------------------------------------------------------------------------
# B10 - image built from the checkout, not main HEAD
# --------------------------------------------------------------------------------------------

class TestB10DockerBuild:

    def test_dockerfile_copies_checkout(self):
        text = (REPO / 'docker' / 'Dockerfile').read_text()
        assert 'git clone' not in text
        assert re.search(r'^COPY .*igver', text, re.M)
        assert 'GIT_SHA' in text and 'org.opencontainers.image.revision' in text
        assert '/opt/igver/BUILD_SHA' in text

    def test_ci_context_is_repo_root(self):
        text = (REPO / '.github' / 'workflows' / 'docker-publish.yml').read_text()
        assert re.search(r'context:\s*\.\s*$', text, re.M)
        assert 'GIT_SHA=${{ github.sha }}' in text

    def test_dockerignore_excludes_heavy_and_private(self):
        text = (REPO / '.dockerignore').read_text().split()
        for pattern in ['.git', 'test/', 'docs/', '*.bam', '*.bai', '*.cram',
                        'igver_agent/', 'igver-mcp/', 'igver_final_test/', 'CLAUDE/', '.claude/']:
            assert pattern in text, pattern


# --------------------------------------------------------------------------------------------
# B12 - BED start is 0-based
# --------------------------------------------------------------------------------------------

class TestB12BedCoordinates:

    def test_goto_is_one_based_filename_keeps_bed(self, tmp_path):
        bed = _write(tmp_path / 'r.hg19.bed', 'chr1\t100\t200\n')
        png, content = _parse_bed_file(bed, str(tmp_path))
        assert _gotos(content) == ['chr1:101-200']
        assert _names(png) == ['chr1-100-200.png']


# --------------------------------------------------------------------------------------------
# behaviour that must be preserved
# --------------------------------------------------------------------------------------------

class TestPreserved:

    def test_display_mode_targets_alignment_tracks(self, tmp_path):
        batch, _ = core.create_batch_script([str(TEST_BAM), str(tmp_path / 'g.hg19.bed')],
                                            [REGION], str(tmp_path))
        lines = open(batch).read().splitlines()
        assert 'squish test_tumor.bam' in lines and 'squish' not in lines

    def test_methylation_injects_color_by(self, tmp_path):
        _, rec = _run_cli(['-i', str(TEST_BAM), '-r', REGION, '-o', str(tmp_path / 'o'),
                           '-g', 'hg19', '--no-singularity', '--methylation'])
        assert 'colorBy BASE_MODIFICATION' in rec['batches'][0].splitlines()

    def test_single_txt_track_list(self, tmp_path):
        lst = _write(tmp_path / 'tracks.txt', f'{TEST_BAM}\n')
        _, rec = _run_cli(['-i', lst, '-r', REGION, '-o', str(tmp_path / 'o'),
                           '-g', 'hg19', '--no-singularity'])
        assert f'load {TEST_BAM}' in rec['batches'][0].splitlines()
