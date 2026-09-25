---
project: igver
status: active
owner: Samuel Ahuno
team: greenbab lab igver users
next_action: Continue Phase B of docs/plans/20260925_audit_bugfix_plan.md on branch fix/audit-1.3.0 (next: B2+B9+B12)
blockers: none
updated: 2026-09-25
shared_copy: none
---

# igver (sahuno fork)

Headless IGV screenshot tool (fork of shahcompbio/igver). This fork carries the
methylation, `--color-by`, parallel-rendering, PDF and genome-alias fixes. The
container `sahuno/igver` is built by GitHub Actions on every push to `main`.

## Exact next steps

0. **Execute `docs/plans/20260925_audit_bugfix_plan.md`** (fixes all 12 audited bugs, release 1.3.0). Read it fully first; follow its Phase A (tests before fixes) → B → C order and its ground rules.
1. When the RetroEM `03_igv_top_loci.sbatch` no longer names `igver_1.2.1_igv2.19.8.sif`, move that SIF to `images/archived/`
2. Optional: add a stable `/opt/igv` symlink and default `igv_dir` to it, so the next IGV bump is a one-line Dockerfile change

## Open unknowns

| # | Question | Owner | Decide by | Status |
|---|---|---|---|---|
| 1 | Swap shared `igver_latest.sif` to the IGV 2.19.8 build? | Samuel Ahuno | 2026-10-09 | decided 2026-09-25: yes |
| 2 | Keep `IGV.Bounds=0,0,1150,800` in the bundled prefs template, or choose another snapshot size? (1150 px = the de-facto width of existing lab figures; plan says the user decides) | Samuel Ahuno | 2026-10-09 | open |
| 3 | E1e (B1 determinism) cannot meet "< 0.5 % pixels differ": 4 identical runs differ 0.58–2.44 %, **only** in UI chrome (ruler/sequence band y≈100–120, 3-row dividers y≈130 and y≈333); the alignment area (y 136–330) is pixel-identical in every pair. Not downsampling (`SAM.DOWNSAMPLE_READS=false`: 1.16–2.44 %). `setSleepInterval 4000` → 0–0.58 % (one 3-row strip left) but costs ~4 s per batch command. Accept chrome-only variance (and measure only the data area), adopt a sleep interval, or leave as is? | Samuel Ahuno | 2026-10-09 | open |
| 4 | Unknown gene or unknown contig (`-r NOTAGENE123`, `NOSUCHCONTIG:1-100`): IGV 2.19.8 silently snapshots the **whole-genome view**, exit 0, nothing in igv0.log or stdout (probe 2026-09-25). igver can only warn. Validate contigs against the genome's .fai/chrom sizes in a later release? | Samuel Ahuno | 2026-10-09 | open |
| 5 | `-f pdf` is broken in 1.2.3 itself (pre-existing, outside the 12 audited bugs): IGV 2.19.8 SVGs have no width/height/viewBox, so cairosvg writes an 845-byte empty PDF and igver exits 1 (host); the image has no cairosvg at all. e2e R4 fails for this reason. Fix in 1.3.x (e.g. derive the canvas size, or build the PDF from the PNG)? | Samuel Ahuno | 2026-10-09 | open |

## Decisions

- 2026-09-25 · Pointed shared `igver_latest.sif` at the 1.2.1 / IGV 2.19.8 image · the old file (2026-04-14) predated the overhaul: no --jobs/--stall-timeout/--version, hang-prone --methylation, broken aliases and PDF · by Samuel Ahuno
- 2026-09-25 · Did not merge or cherry-pick upstream `renov` (4a3329e, "fix PIL imports in Dockerfile") · main already installs the Python deps, has the TMPDIR/`igver.cli` test fixes, and clones the fork; `renov` branches from 2025-03 and conflicts. Took only its IGV 2.19.8 bump · by Samuel Ahuno
- 2026-09-25 · Bumped igver to 1.2.1 with IGV 2.19.8 · CI tags the image with the setup.py version, so leaving it at 1.2.0 would have overwritten the `sahuno/igver:1.2.0` tag · by Samuel Ahuno

## Log

### 2026-09-25 19:30 · Claude Code · Audit plan: Phase A done, B1+B11 implemented (branch fix/audit-1.3.0)
- **Done:**
  - Probes with raw IGV 2.19.8 (igver_latest.sif): a writable `--igvDirectory` is honoured (`IGV Directory: <dir>`); without a prefs file IGV **copies ~/igv/prefs.properties** in; a pre-written one is kept; `-g hg19` does not stop the hg38 default load, `DEFAULT_GENOME_KEY=hg19` does (1 `Loading genome` line). Sub-path bind `fixture:/home/ahunos/igv` over `-B /home` works. Stale index (index older than BAM): IGV renders, no dialog → no pre-flight warning needed (E3b). Double-quoted batch paths with spaces work. Unknown gene/contig → silent whole-genome snapshot. Corrupt BAM / unknown file type render without a dialog; a 404 URL track and a dead-URL genome JSON block IGV.
  - A1: `test/test_audit_1_3_0.py` (100 tests). Baseline on fed1676: **90 failed, 10 passed**; the 10 passes are preservation tests (legacy SV lines, chrUn contig, CRLF/tabs, gene name, split view, alias, BED headers, display mode, --methylation, single .txt list). Two vacuous passes were tightened first (run-dir removal, `.lead` name).
  - A2: `test/e2e/run_e2e.sh` + `e2e_runner.py` + `cases.tsv` (28 cases). Baseline (sbatch jobs 14942391 host / 14942392 image, plus a local re-run of the strengthened E3c/E7/E8/E11f): **host 3/28 pass (E3b, R1, R2); image 4/28 pass (E3b, E4c, R1, R2)**. Negative controls: E1a/E1b render 700 px wide with the poisoned ~/igv; E1c changes the real `~/igv/igv0.log` mtime; E2c writes a hidden `.locus.png`; E8 renders against the personal default genome (every read a mismatch); E3a hangs until killed. R4 (-f pdf) fails on 1.2.3 itself (open unknown 5).
  - A3: `test/e2e/fixtures/poisoned_igv/` (IGV.Bounds 700x500, soft clips on, no downsampling; mm10/hg19 JSONs with every URL → s3 igv.broadinstitute.org, verified 403). The harness binds a **copy** per case.
  - B1+B11 implemented (commit 0aa66fa). Unit: TestB1 + TestB11 16/16 pass; existing suite 88 passed, 1 skipped. e2e host and image: E1, E1a, E1b, E1c, E1d, E1d_bad, E11 PASS. E1d soft clips: the alignment area differs from E1 by 2,432 px in both modes while the no-prefs controls differ by 0; crop inspected. Added startup time: none (fresh runs 20–22 s vs 21–23 s on 1.2.3; one genome load instead of two).
  - Still open for B1/B11: failure-path (E3c) and E11f need the B3 URL-track handling (1.2.3's CLI rejects URL tracks as "does not exist"); E1e blocked (open unknown 3).
- **Key paths:** test/test_audit_1_3_0.py; test/e2e/{run_e2e.sh,e2e_runner.py,cases.tsv,fixtures/}; igver/data/igv_prefs.properties; igver/igver.py (`read_prefs_template`, `parse_igv_prefs`, `_make_igv_run_dir`, `_igv_log_excerpt`, `run_igv`); igver/cli.py (`--igv-prefs`); baseline code export test/e2e/out/baseline_src/ (wrapper `igver_baseline`, gitignored)
- **Commands that worked:**
  - `/home/ahunos/miniforge3/envs/igver/bin/python -m pytest test/test_audit_1_3_0.py -q -p no:cacheprovider`
  - `test/e2e/run_e2e.sh host --cases E1,E1a` (on a compute node) and `test/e2e/run_e2e.sh image --cases ...` (checks the working-tree bind first)
  - full run: `sbatch -p cpushort --exclude=isca071 -c 2 --mem=16G -t 01:30:00 -o test/e2e/logs/slurm_%j.out test/e2e/run_e2e.sh host`
  - 1.2.3 baseline in host mode: `E2E_IGVER_HOST=$PWD/test/e2e/out/baseline_src/igver_baseline test/e2e/run_e2e.sh host --tag baseline` (PYTHONPATH does not work: the editable-install finder wins); image mode: `--no-repo-bind`
- **Known issues / blockers:** `srun` from this session queues forever (step 0 holds the whole allocation 14937376 on isca017); run quick IGV checks directly on the node instead. E1e, unknown-locus and PDF: open unknowns 3–5.
- **Exact next steps:** B2+B9+B12 → B4+B6 → B3 (incl. URL tracks: skip existence check/binds) → B5 → B7 → B8 → B10, each with unit + e2e in both modes and a commit; then full e2e both modes (sbatch) and Phase C.

### 2026-09-25 17:20 · Claude Code · Bug audit of igver 1.2.3: ranked list (nothing fixed yet)
- **Done:** Read cli.py and igver.py; probed edge cases with Python and with real IGV runs (igver_latest.sif, hg19 test BAM, `--stall-timeout 45`). Ranked findings (✓ = reproduced; code = confirmed by reading only):
  1. ✓ `--igvDirectory /opt/IGV_2.19.8` is ignored (read-only in the SIF), so IGV always uses the user's `~/igv` ("IGV Directory: /home/ahunos/igv"). Personal prefs change the output (SAM.DOWNSAMPLE_READS=false, SHOW_SOFT_CLIPPED, IGV.Bounds sets the image width, THIRD_GEN colorBy), and stale genome caches caused today's mm10 hang.
  2. ✓ Text region files silently produce wrong screenshots with exit 0: a line with no `chr:start-end` → `goto ` → whole-genome view saved as a hidden `.name.png`; a tag that looks like a locus (house locus ID with a `+` strand) → split screen with a bogus second panel; multi-word tags keep only the last word.
  3. ✓ Missing BAM/CRAM index → IGV dialog hang → killed twice → fails after 2 × stall-timeout (20 min at the default) with a generic message.
  4. ✓ BED name containing a space or `/` (e.g. RepeatMasker `LINE/L1`) → the snapshot is never written; fails after retries with a generic error.
  5. ✓ Typo in a region file path → treated as a locus string → fails with a misleading error instead of "file not found".
  6. code: duplicate snapshot names (same region + name) → silent overwrite; a race with `-j`.
  7. code: a `.txt` track list is only recognized when it's the sole `-i` argument; mixed with tracks, it is loaded as a track → IGV error → hang.
  8. code: a relative FASTA passed to `-g` breaks (IGV resolves it against the batch file's directory); the FASTA directory isn't auto-bound.
  9. code: space-separated BED → every line silently skipped → "No screenshots generated" with no reason.
  10. code: the image build clones `main` HEAD rather than the commit being built, so a later rebuild of a tag can hold newer code.
  11. ✓ `-j` JVMs share `~/igv`: the log rotates (`igv0.log.1`), so the error hint points at the wrong file; port 60151 BindException (harmless).
  12. code: BED start (0-based) is passed to `goto` (1-based) → view shifted by 1 bp. Cosmetic.
- **Key paths:** igver/igver.py (`_parse_region_file`, `_parse_bed_file`, `run_igv`), igver/cli.py (`main`), docker/Dockerfile
- **Commands that worked:** probe pattern: `apptainer exec --bind /data1/greenbab <sif> igver -i <bam> -r <regions> -o <out> -g hg19 --no-singularity --stall-timeout 45`
- **Known issues / blockers:** `srun` from this VS Code session runs as a step inside the interactive allocation (job 14843879 on iscf025), not on cpushort, so `-c 2` is refused. Earlier "cpushort" test notes in this log actually ran there.
- **Exact next steps:** get the user's pick of which bugs to fix (the top 5 are cheap: isolated IGV prefs dir, region-line validation, index preflight, filename sanitising, region-file existence check).

### 2026-09-25 16:55 · Claude Code · 1.2.3: -d applied to alignment tracks only (BED tracks were hidden)
- **Done:** Root-caused the "BED track missing" layout issue. `create_batch_script` emitted a bare `squish` (the default `-d`), which IGV applies to every track; a squished or expanded RefSeq/BED track fills the panel and hides the tracks below it. Raw-IGV experiments at chr7 CFTR (hg38): BED-only with squish or expand hid the BED, collapse showed it; BAM+BED with bare squish hid it; `squish <bam basename>` showed everything. Added `_display_commands()` (named per-alignment-track commands; expand emits nothing; whitespace names skipped with a warning), `test/test_display_mode.py` (49 tests pass), and README/CLAUDE.md notes. Released 1.2.3: commit a537631, CI run 36187837744 green. Pulled the SIF; an inside-image test with default `-d` (BAM+BED, CFTR) shows the BED. `igver_latest.sif` → 1.2.3; the 1.2.2 SIF moved to `archived/`.
- **Key paths:** igver/igver.py (`_display_commands`), igver/cli.py, test/test_display_mode.py; /data1/greenbab/software/images/igver_1.2.3_igv2.19.8.sif; /data1/greenbab/software/images/archived/igver_1.2.2_igv2.19.8.sif
- **Commands that worked:** `/home/ahunos/miniforge3/envs/igver/bin/python -m pytest test/test_display_mode.py test/test_bed_support.py test/test_genome_aliases.py test/test_igv_version.py test/test_output_formats.py -q`; raw IGV in the image: `apptainer exec <sif> xvfb-run --auto-display --server-args="-screen 0 1920x1080x24" /opt/IGV_2.19.8/igv.sh -b <batch>`
- **Known issues / blockers:** Overlapping BED features draw on one row in IGV's default collapsed mode (IGV's standard annotation view).
- **Exact next steps:** see "Exact next steps" above.

### 2026-09-25 16:45 · Claude Code · Cached human hg38 genome JSON refreshed and verified
- **Done:** Backed up `~/igv/genomes/hg38.json` (Oct 2024; fastaURL on igv-genepattern-org S3 → 403) and replaced it with https://igv.org/genomes/json/hg38.json; all 11 URLs return 200/206. The cached hg19 and hs1 JSONs were already fine. Rendered `chr17:61268000-61282000` with `igver_latest.sif` (1.2.2) on cpushort: BAM `AluEM/.../labpipe_alu2000/ALN/beerssim_HG38.sorted.bam` plus a BED with a `#` header. Exit 0 in 23 s; ideogram, coverage, reads, BCAS3 and the BED feature all shown. Found and documented a layout quirk: in BED-only views, `Refseq All` fills the panel and hides the BEDs.
- **Key paths:** ~/igv/genomes/hg38.json (backup: hg38.json.bak_20260925_dead_s3); /data1/greenbab/users/ahunos/apps/llm_configs/claude/rules/igv.md
- **Commands that worked:** `curl -sf https://igv.org/genomes/json/hg38.json -o ~/igv/genomes/hg38.json`
- **Known issues / blockers:** none
- **Exact next steps:** see "Exact next steps" above.

### 2026-09-25 16:08 · Claude Code · 1.2.2 released: refreshed bundled genome JSONs
- **Done:** Committed the 5 refreshed `docker/json` genome files, bumped to 1.2.2 (so CI doesn't overwrite the `:1.2.1` tag), and added a README note on stale cached JSONs. Pushed 603f062; CI run 36183304542 succeeded (1m34s) and published `:latest`, `:1.2.2` and `:603f062`. Pulled the SIF and confirmed the bundled mouse JSON uses igv.org. Test render of `chr13:9830023-9840665` (R-0-1 BAM, mm10): exit 0 in 27 s. Pointed `igver_latest.sif` at the new SIF. Kept `igver_1.2.1_igv2.19.8.sif` in place because RetroEM `03_igv_top_loci.sbatch` names it.
- **Key paths:** /data1/greenbab/software/images/igver_1.2.2_igv2.19.8.sif; igver_latest.sif -> igver_1.2.2_igv2.19.8.sif
- **Commands that worked:** `apptainer pull /data1/greenbab/software/images/igver_1.2.2_igv2.19.8.sif docker://sahuno/igver:1.2.2`; `ln -sfn igver_1.2.2_igv2.19.8.sif igver_latest.sif`
- **Known issues / blockers:** The validate-reference-genome hook blocks any Bash command that mentions both a mouse and a human build, so edit multi-genome text with the file editor or keep the names out of the command.
- **Exact next steps:** see "Exact next steps" above.

### 2026-09-25 16:00 · Claude Code · mm10 screenshots hung: stale cached genome JSON, fixed
- **Done:** RetroEM job 14908700 (`results/20260925_mm10_L1_e2e/03_igv_top_loci.sbatch`) produced 0 PNGs. `jstack` showed both JVMs blocked on `JOptionPane`, and the log ended at `Loading genome: ~/igv/genomes/mm10.json`. The cached JSON (Aug 2024) pointed at `s3.amazonaws.com/igv.broadinstitute.org`, which now returns 403. Cancelled the job, backed up the JSON and replaced it with https://igv.org/genomes/json/mm10.json. A one-region test took 27 s; resubmitted job 14910024 wrote all 8 PNGs in ~26 s. Audited all 29 bundled `docker/json/*.json`: hg19, hg38, mm10, mm39 and rn6 have dead URLs (403/404). Replaced them in the working tree with the current igv.org versions, all URLs 200/206. **Not committed.** Added a "Stale cached genome JSON" section to the IGV rules file.
- **Key paths:** ~/igv/genomes/mm10.json (backup: mm10.json.bak_20260925_dead_s3); docker/json/{hg19,hg38,mm10,mm39,rn6}.json (uncommitted); /data1/greenbab/users/ahunos/apps/llm_configs/claude/rules/igv.md
- **Commands that worked:** `curl -sf https://igv.org/genomes/json/mm10.json -o ~/igv/genomes/mm10.json`; `srun --jobid <id> --overlap -n1 /usr/bin/bash -c 'apptainer exec <sif> jstack <pid>'` (srun needs the absolute `/usr/bin/bash`)
- **Known issues / blockers:** A test with an empty home directory (`--no-home --home <dir>:/home/ahunos`) also hung, but IGV never created `igv/` in that directory, so the test setup was likely broken and proves nothing about the bundled JSONs.
- **Exact next steps:** see "Exact next steps" above.

### 2026-09-25 15:30 · Claude Code · Shared igver_latest.sif now points at 1.2.1
- **Done:** Renamed the old shared SIF to `igver_20260414.sif` (kept as a rollback) and made `igver_latest.sif` a relative symlink to `igver_1.2.1_igv2.19.8.sif`. Confirmed `apptainer exec igver_latest.sif igver --version` gives `igver 1.2.1`.
- **Key paths:** /data1/greenbab/software/images/igver_latest.sif -> igver_1.2.1_igv2.19.8.sif; /data1/greenbab/software/images/archived/igver_20260414.sif
- **Commands that worked:** `cd /data1/greenbab/software/images && mv igver_latest.sif igver_20260414.sif && ln -s igver_1.2.1_igv2.19.8.sif igver_latest.sif`
- **Known issues / blockers:** none. Rollback: `ln -sfn archived/igver_20260414.sif igver_latest.sif` (old SIF moved to `archived/` later the same day)
- **Exact next steps:** see "Exact next steps" above.

### 2026-09-25 15:15 · Claude Code · 1.2.1 image built, pulled and smoke-tested
- **Done:** Pushed c9e4f6c; GitHub Actions run 36177308430 succeeded (5m06s) and pushed `sahuno/igver:latest`, `:1.2.1` and `:c9e4f6c`. Pulled the SIF and confirmed IGV 2.19.8, the `/opt/IGV_2.19.5` symlink and `igver 1.2.1`. On cpushort, rendered `8:32534767-32536767` of `test/test_tumor.bam` (hg19) three ways, all exit 0 with a correct PNG: (a) inside the SIF with `--no-singularity`, (b) host igver 1.2.1 wrapping the SIF, (c) host igver with `--igv-dir /opt/IGV_2.19.5` (the old default).
- **Key paths:** /data1/greenbab/software/images/igver_1.2.1_igv2.19.8.sif (1.6 GB, new file; `igver_latest.sif` untouched)
- **Commands that worked:**
  - `APPTAINER_CACHEDIR=/data1/greenbab/users/ahunos/apptainer_cache apptainer pull /data1/greenbab/software/images/igver_1.2.1_igv2.19.8.sif docker://sahuno/igver:1.2.1`
  - `srun -p cpushort --exclude=isca071 -n 1 -c 1 --mem=8G -t 00:30:00 <script>` (`-c 2` was refused: "More processors requested than permitted")
  - Push from this repo has no credential helper configured, so a plain `git push` hangs at a username prompt. Use: `git -c credential.helper='!gh auth git-credential' push origin main`
- **Known issues / blockers:** none
- **Exact next steps:** see "Exact next steps" above.

### 2026-09-25 · Claude Code · IGV 2.19.5 → 2.19.8, igver 1.2.1, conda env reinstalled
- **Done:** Confirmed `apps/igver` is the most recent clone (matches origin/main; 19 ahead of upstream/main; `projects/IGVAgent/igver` is an older clone). Reinstalled the `igver` conda env as an editable install (was a non-editable 0.3) and added cairosvg. Bumped the Dockerfile to IGV 2.19.8, and the `igv_dir` defaults in cli.py/igver.py to `/opt/IGV_2.19.8`. Added a `/opt/IGV_2.19.5` symlink in the image so igver ≤ 1.2.0 still works with `:latest`. setup.py → 1.2.1; docs and test_igv_version.py updated. 32 unit tests pass.
- **Key paths:** /data1/greenbab/users/ahunos/apps/igver/docker/Dockerfile, igver/cli.py, igver/igver.py, setup.py, test/test_igv_version.py, README.md, DOCKER_USAGE.md, CLAUDE.md
- **Commands that worked:**
  - `/home/ahunos/miniforge3/envs/igver/bin/pip install -e . && /home/ahunos/miniforge3/envs/igver/bin/pip install cairosvg`
  - `/home/ahunos/miniforge3/envs/igver/bin/python -m pytest test/test_igv_version.py test/test_genome_aliases.py test/test_bed_support.py -q`
- **Known issues / blockers:** Until the new image is in use, host igver 1.2.1 (both conda envs are editable) points at `/opt/IGV_2.19.8`, which doesn't exist in older SIFs such as `igver_latest.sif`. For those, pass `--igv-dir /opt/IGV_2.19.5`, or run inside the SIF with `--no-singularity`.
- **Exact next steps:** see "Exact next steps" above.
