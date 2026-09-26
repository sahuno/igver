#!/usr/bin/env python3
"""
igver end-to-end case runner (called by test/e2e/run_e2e.sh).

Author: Samuel Ahuno
Date: 2026-09-25
Purpose: run every case in test/e2e/cases.tsv in one run mode (host-wrapper or in-image) against real
         IGV and assert exit code, exact output file list, elapsed time, output greps and PNG checks.

Usage:
    python e2e_runner.py --mode host|image [--cases E1,E2a] [--no-repo-bind] [--sif PATH]

Prints one `PASS|FAIL <case> <reason>` line per case plus a summary, writes a results TSV next to
the log, and exits 1 if any case failed.
"""
import argparse
import hashlib
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time

from PIL import Image, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
FIX = os.path.join(HERE, 'fixtures')
APPTAINER = '/home/ahunos/miniforge3/envs/snakemake/bin/apptainer'
IGVER_HOST = os.environ.get('E2E_IGVER_HOST', '/home/ahunos/miniforge3/envs/igver/bin/igver')
DEFAULT_SIF = '/data1/greenbab/software/images/igver_latest.sif'
PDFTOPPM = '/home/ahunos/miniforge3/envs/r-env/bin/pdftoppm'
PLACEHOLDERS = {
    'BAM': os.path.join(REPO, 'test', 'test_tumor.bam'),
    'FIX': FIX,
    'HG38_BAM': '/data1/greenbab/projects/AluEM/MDA5_protection_paper/Beers2/labpipe_alu2000/ALN/'
                'beerssim_HG38.sorted.bam',
    'MM10_BAM': '/data1/greenbab/projects/triplicates_epigenetics_diyva/RNA/rerun_RNASeq_11032025/ALN/'
                'R-0-1_MM38.sorted.bam',
}
BATCH_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.batch$')
HOME_IGV = os.path.expanduser('~/igv')


def load_cases(path):
    """
    Read cases.tsv into a list of dicts (comment lines skipped).

    Parameters:
        path (str): TSV with columns case_id mode args expect_exit expect_files max_seconds checks notes.

    Returns:
        list of dict: one per case, in file order.

    Example:
        >>> load_cases('cases.tsv')[0]['case_id']
        'E1'
    """
    rows, header = [], None
    for line in open(path):
        line = line.rstrip('\n')
        if not line or line.startswith('#'):
            continue
        fields = line.split('\t')
        if header is None:
            header = fields
            continue
        fields += [''] * (len(header) - len(fields))
        rows.append(dict(zip(header, fields)))
    return rows


def home_state():
    """Return (igv0.log mtime, prefs.properties sha1) of the real ~/igv."""
    log = os.path.join(HOME_IGV, 'igv0.log')
    prefs = os.path.join(HOME_IGV, 'prefs.properties')
    mtime = os.path.getmtime(log) if os.path.exists(log) else None
    sha = hashlib.sha1(open(prefs, 'rb').read()).hexdigest() if os.path.exists(prefs) else None
    return mtime, sha


def pixel_diff(a, b):
    """
    Compare two images.

    Returns:
        (bool, float): (same dimensions, fraction of differing pixels; 1.0 if dimensions differ).
    """
    ia, ib = Image.open(a).convert('RGB'), Image.open(b).convert('RGB')
    if ia.size != ib.size:
        return False, 1.0
    diff = ImageChops.difference(ia, ib).convert('L')
    changed = sum(1 for v in diff.getdata() if v)
    return True, changed / (ia.size[0] * ia.size[1])


def build_command(mode, args, out, overlay, sif, bind_repo):
    """Build the argv for one case in the given run mode."""
    if mode == 'host':
        cmd = [IGVER_HOST] + args + ['-o', out, '--singularity-image', sif]
        if overlay:
            cmd += ['--singularity-args', f'-B /home -B {overlay}:{HOME_IGV}']
        return cmd
    cmd = [APPTAINER, 'exec', '--bind', '/data1/greenbab']
    if bind_repo:
        cmd += ['--bind', f'{REPO}:/opt/igver']
    if overlay:
        cmd += ['--bind', f'{overlay}:{HOME_IGV}']
    return cmd + [sif, 'igver'] + args + ['-o', out, '--no-singularity']


def verify_repo_bind(sif):
    """Abort unless the in-image igver really is the working tree (plan §3.2)."""
    # --pwd /: from the repo root, `import igver` would find the checkout through the cwd instead
    base = [APPTAINER, 'exec', '--pwd', '/', '--bind', '/data1/greenbab', '--bind', f'{REPO}:/opt/igver', sif]
    inside = subprocess.run(base + ['sha1sum', '/opt/igver/igver/igver.py'],
                            capture_output=True, text=True).stdout.split()[:1]
    host = hashlib.sha1(open(os.path.join(REPO, 'igver', 'igver.py'), 'rb').read()).hexdigest()
    where = subprocess.run(base + ['python', '-c', 'import igver; print(igver.__file__)'],
                           capture_output=True, text=True).stdout.strip()
    print(f"[bind check] in-image sha1={inside} host sha1={host} igver.__file__={where}")
    if inside != [host] or not where.startswith('/opt/igver/'):
        sys.exit('[bind check] FAILED: in-image igver is not the working tree')


def run_case(case, mode, sif, bind_repo, outroot, done):
    """
    Run one case and evaluate every expectation.

    Returns:
        (bool, str, float): (passed, reason, elapsed seconds).
    """
    cid = case['case_id']
    out = os.path.join(outroot, cid)
    tmp, setup = out + '.tmp', out + '.setup'
    for d in (out, tmp, setup):
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d)
    checks = [c for c in case['checks'].split(';') if c]
    subs = dict(PLACEHOLDERS, OUT=out, SETUP=setup)

    overlay = None
    if 'overlay:poisoned' in checks:
        overlay = os.path.join(setup, 'poisoned_igv')  # a copy: IGV writes into its directory
        shutil.copytree(os.path.join(FIX, 'poisoned_igv'), overlay)
    if 'setup:stale_index' in checks:
        shutil.copy(PLACEHOLDERS['BAM'] + '.bai', setup)
        shutil.copy(PLACEHOLDERS['BAM'], setup)
        os.utime(os.path.join(setup, 'test_tumor.bam.bai'), (946684800, 946684800))  # 2000-01-01

    args = shlex.split(re.sub(r'\{(\w+)\}', lambda m: subs[m.group(1)], case['args']))
    cmd = build_command(mode, args, out, overlay, sif, bind_repo)
    env = {k: v for k, v in os.environ.items() if k not in ('APPTAINER_BIND', 'SINGULARITY_BIND')}
    env['TMPDIR'] = tmp
    env['PATH'] = os.path.dirname(APPTAINER) + ':' + env.get('PATH', '')

    before = home_state()
    max_s = float(case['max_seconds'])
    start = time.time()
    proc = subprocess.Popen(cmd, cwd=FIX, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            start_new_session=True)
    try:
        output, _ = proc.communicate(timeout=max_s + 60)
        timed_out = False
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        output, _ = proc.communicate()
        timed_out = True
    elapsed = time.time() - start
    output = output.decode(errors='replace')
    with open(out + '.output.txt', 'w') as f:
        f.write(shlex.join(cmd) + '\n\n' + output)

    fails = []
    if timed_out:
        fails.append(f'hard timeout ({max_s + 60:.0f}s)')
    if proc.returncode != int(case['expect_exit']):
        fails.append(f"exit {proc.returncode} != {case['expect_exit']}")
    if elapsed > max_s:
        fails.append(f'elapsed {elapsed:.1f}s > {max_s:.0f}s')
    listing = sorted(os.listdir(out))
    kept = [f for f in listing if BATCH_RE.match(f)]
    got = [f for f in listing if not BATCH_RE.match(f)]
    want = sorted(f for f in case['expect_files'].split(';') if f and f != '-')
    if got != want:
        fails.append(f'files {got} != {want}')
    pngs = [os.path.join(out, f) for f in got if f.endswith('.png')]

    for check in checks:
        kind, _, arg = check.partition(':')
        if kind == 'grep' and not re.search(arg, output):
            fails.append(f'no match for /{arg}/')
        elif kind == 'nogrep' and re.search(arg, output):
            fails.append(f'unexpected match for /{arg}/')
        elif kind == 'count':
            pattern, _, n = arg.rpartition('=')
            found = len(re.findall(pattern, output))
            if found != int(n):
                fails.append(f'/{pattern}/ matched {found}x, want {n}')
        elif kind == 'width':
            for p in pngs:
                w = Image.open(p).size[0]
                if w != int(arg):
                    fails.append(f'{os.path.basename(p)} width {w} != {arg}')
        elif kind == 'tmp_clean':
            left = [d for d in os.listdir(tmp) if d.startswith('igver_')]
            if left:
                fails.append(f'run dirs left in TMPDIR: {left}')
        elif kind == 'identical_to':
            for p in pngs:
                q = os.path.join(outroot, arg, os.path.basename(p))
                if not os.path.exists(q):
                    fails.append(f'identical_to: {q} missing')
                    continue
                same_dims, frac = pixel_diff(p, q)
                print(f'    {cid} vs {arg}: same_dims={same_dims} differing_pixels={frac:.5%}')
                if not same_dims or frac:
                    fails.append(f'not pixel-identical to {arg}: dims={same_dims} frac={frac:.4%}')
        elif kind == 'repeat':
            first = {f: hashlib.md5(open(os.path.join(out, f), 'rb').read()).hexdigest() for f in got}
            for n in range(2, int(arg) + 1):
                rep = f'{out}.rep{n}'
                shutil.rmtree(rep, ignore_errors=True)
                os.makedirs(rep)
                rcmd = [rep if c == out else c for c in cmd]
                r = subprocess.run(rcmd, cwd=FIX, env=env, capture_output=True, timeout=max_s + 60)
                digests = {f: hashlib.md5(open(os.path.join(rep, f), 'rb').read()).hexdigest()
                           for f in sorted(os.listdir(rep)) if not BATCH_RE.match(f)}
                differ = [f for f in first if digests.get(f) != first[f]]
                print(f'    {cid} run {n}: exit {r.returncode}, {len(digests)} files, {len(differ)} differ from run 1')
                if r.returncode or differ or set(digests) != set(first):
                    fails.append(f'run {n}: exit {r.returncode}, differing {differ}')
        elif kind == 'svg_sized':
            for svg in [os.path.join(out, f) for f in got if f.endswith('.svg')]:
                root = re.search(r'<svg\b[^>]*>', open(svg).read())
                if not root or 'viewBox=' not in root.group(0):
                    fails.append(f'{os.path.basename(svg)} has no viewBox')
        elif kind == 'pdf_width':
            for pdf in [os.path.join(out, f) for f in got if f.endswith('.pdf')]:
                size = os.path.getsize(pdf)
                prefix = os.path.join(out + '.setup', 'pdf_raster')
                r = subprocess.run([PDFTOPPM, '-png', '-r', '300', '-singlefile', pdf, prefix],  # page = canvas at --dpi 300
                                   capture_output=True, text=True)
                w = Image.open(prefix + '.png').size[0] if r.returncode == 0 else None
                print(f'    {cid}: {os.path.basename(pdf)} {size} bytes, rasterised width {w}')
                if size < 20000 or w != int(arg):
                    fails.append(f'{os.path.basename(pdf)}: {size} bytes, raster width {w} (want > 20 KB, {arg} px)')
        elif kind == 'home_untouched':
            after = home_state()
            if after != before:
                fails.append(f'~/igv changed: {before} -> {after}')
        elif kind == 'rundirs':
            dirs = set(re.findall(r'igver_igv_[A-Za-z0-9_]+', output))
            if len(dirs) < int(arg):
                fails.append(f'{len(dirs)} distinct run dirs in output, want >= {arg}')
        elif kind in ('same_as', 'differs_from'):
            other = os.path.join(outroot, arg)
            if arg not in done:
                fails.append(f'{kind}: case {arg} did not run first')
                continue
            for p in pngs:
                q = os.path.join(other, os.path.basename(p))
                if not os.path.exists(q):
                    fails.append(f'{kind}: {q} missing')
                    continue
                same_dims, frac = pixel_diff(p, q)
                print(f'    {cid} vs {arg}: same_dims={same_dims} differing_pixels={frac:.5%}')
                if kind == 'same_as' and not (same_dims and frac < 0.005):
                    fails.append(f'differs from {arg}: dims={same_dims} frac={frac:.4%}')
                if kind == 'differs_from' and same_dims and frac == 0:
                    fails.append(f'identical to {arg}')
    if kept:
        print(f'    {cid}: kept batch file(s) {kept}')
    return (not fails), '; '.join(fails) or 'ok', elapsed


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--mode', choices=['host', 'image'], required=True)
    ap.add_argument('--cases', help='comma-separated case ids (default: all for this mode)')
    ap.add_argument('--sif', default=DEFAULT_SIF)
    ap.add_argument('--no-repo-bind', action='store_true',
                    help='image mode: test the image as shipped (release gate), not the working tree')
    ap.add_argument('--tag', default='', help='suffix for the output directory (e.g. baseline)')
    ap.add_argument('--results', help='results TSV path')
    a = ap.parse_args()

    bind_repo = a.mode == 'image' and not a.no_repo_bind
    if bind_repo:
        verify_repo_bind(a.sif)
    wanted = set(a.cases.split(',')) if a.cases else None
    cases = [c for c in load_cases(os.path.join(HERE, 'cases.tsv'))
             if c['mode'] in (a.mode, 'both') and (wanted is None or c['case_id'] in wanted)]
    outroot = os.path.join(HERE, 'out', a.mode + (f'_{a.tag}' if a.tag else ''))
    os.makedirs(outroot, exist_ok=True)
    print(f'mode={a.mode} sif={os.path.realpath(a.sif)} repo_bind={bind_repo} cases={len(cases)} out={outroot}')

    rows, done = [], set()
    for case in cases:
        ok, reason, elapsed = run_case(case, a.mode, a.sif, bind_repo, outroot, done)
        done.add(case['case_id'])
        status = 'PASS' if ok else 'FAIL'
        print(f"{status} {case['case_id']} ({elapsed:.1f}s) {reason}", flush=True)
        rows.append((case['case_id'], status, f'{elapsed:.1f}', reason))
        if 'visual' in case['checks']:
            print(f"    visual check needed: {os.path.join(outroot, case['case_id'])}")
    n_fail = sum(r[1] == 'FAIL' for r in rows)
    print(f'SUMMARY mode={a.mode}: {len(rows) - n_fail} passed, {n_fail} failed of {len(rows)}')
    if a.results:
        with open(a.results, 'w') as f:
            f.write('case_id\tstatus\telapsed_s\treason\n')
            f.writelines('\t'.join(r) + '\n' for r in rows)
    sys.exit(1 if n_fail else 0)


if __name__ == '__main__':
    main()
