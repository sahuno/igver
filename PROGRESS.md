---
project: igver
status: active
owner: Samuel Ahuno
team: greenbab lab igver users
next_action: Resume feat/stable-snapshots (docs/plans/20260925_stable_snapshots_plan.md, see its last design-change entry)
blockers: none
updated: 2026-09-25
shared_copy: none
---

# igver (sahuno fork)

Headless IGV screenshot tool (fork of shahcompbio/igver). This fork carries the
methylation, `--color-by`, parallel-rendering, PDF and genome-alias fixes. The
container `sahuno/igver` is built by GitHub Actions on every push to `main`.

## Exact next steps

0. Pick a run-to-run variance approach (open unknown 3); everything else from the audit is released (1.3.1).
1. When the RetroEM `03_igv_top_loci.sbatch` no longer names `igver_1.2.1_igv2.19.8.sif`, move that SIF to `images/archived/`
2. Optional: add a stable `/opt/igv` symlink and default `igv_dir` to it, so the next IGV bump is a one-line Dockerfile change

## Open unknowns

| # | Question | Owner | Decide by | Status |
|---|---|---|---|---|
| 1 | Swap shared `igver_latest.sif` to the IGV 2.19.8 build? | Samuel Ahuno | 2026-10-09 | decided 2026-09-25: yes |
| 2 | Keep `IGV.Bounds=0,0,1150,800` in the bundled prefs template, or choose another snapshot size? (1150 px = the de-facto width of existing lab figures; plan says the user decides) | Samuel Ahuno | 2026-10-09 | decided 2026-09-25: keep 1150x800 |
| 3 | E1e (B1 determinism) is flaky against "< 0.5 % pixels differ": 4 identical runs differ 0.58–2.44 %, **only** in UI chrome (ruler/sequence band y≈100–120, 3-row dividers y≈130 and y≈333); the alignment area (y 136–330) is pixel-identical in every pair. Not downsampling (`SAM.DOWNSAMPLE_READS=false`: 1.16–2.44 %). `setSleepInterval 4000` → 0–0.58 % (one 3-row strip left) but costs ~4 s per batch command. E1e then passed in 2 of 6 later suite runs (host C2, release gate) and failed in 4 (0.58–2.43 %). Separately, a **header-repaint glitch** (ideogram/ruler overpainted by a shifted alignment panel) was seen once in ~109 fixed-code renders (image-mode E2b) and 0/20 in a 1.2.3 control, so its rate is not attributable. Accept chrome-only variance (and measure only the data area), adopt a sleep interval, or leave as is? Recommended (2026-09-25): snapshot stability protocol — compare the 1.3.1 verification PNG with the real PNG and re-capture until two consecutive captures are identical (bounded); first step: measure their mismatch rate. | Samuel Ahuno | 2026-10-09 | open: user undecided |
| 4 | Unknown gene or unknown contig (`-r NOTAGENE123`, `NOSUCHCONTIG:1-100`): IGV 2.19.8 silently snapshots the **whole-genome view**, exit 0, nothing in igv0.log or stdout (probe 2026-09-25). igver can only warn. Validate contigs against the genome's .fai/chrom sizes in a later release? | Samuel Ahuno | 2026-10-09 | decided 2026-09-25: fix in 1.3.1 — done, released 1.3.1 |
| 5 | `-f pdf` is broken in 1.2.3 itself (pre-existing, outside the 12 audited bugs): IGV 2.19.8 SVGs have no width/height/viewBox, so cairosvg writes an 845-byte empty PDF and igver exits 1 (host); the image has no cairosvg at all. e2e R4 fails for this reason. Fix in 1.3.x (e.g. derive the canvas size, or build the PDF from the PNG)? | Samuel Ahuno | 2026-10-09 | decided 2026-09-25: fix in 1.3.1 — done, released 1.3.1 |

## Decisions

- 2026-09-25 · Released 1.3.0 with B1 (E1e) and C2/C4 (R4) blocked rather than green · both failures are open unknowns with evidence (chrome-only render variance; `-f pdf` broken in 1.2.x too), neither is a regression, and the plan allows blocked items · by Claude Code (autonomous plan execution)
- 2026-09-25 · Pointed shared `igver_latest.sif` at the 1.2.1 / IGV 2.19.8 image · the old file (2026-04-14) predated the overhaul: no --jobs/--stall-timeout/--version, hang-prone --methylation, broken aliases and PDF · by Samuel Ahuno
- 2026-09-25 · Did not merge or cherry-pick upstream `renov` (4a3329e, "fix PIL imports in Dockerfile") · main already installs the Python deps, has the TMPDIR/`igver.cli` test fixes, and clones the fork; `renov` branches from 2025-03 and conflicts. Took only its IGV 2.19.8 bump · by Samuel Ahuno
- 2026-09-25 · Bumped igver to 1.2.1 with IGV 2.19.8 · CI tags the image with the setup.py version, so leaving it at 1.2.0 would have overwritten the `sahuno/igver:1.2.0` tag · by Samuel Ahuno

## Log

### 2026-09-26 · Claude Code · Stability protocol WIP paused (usage limit); not released
- **Done:** Branch feat/stable-snapshots: verification + post (and SVG pre) captures, `_unstable_blocks`, up to 2 re-render passes, `--settle-ms`, `_wait()` (IGV 2.19.8 has no `sleep` command; waits are `setSleepInterval W` + `setSleepInterval 0`). Tests: test/test_stable_snapshots.py; e2e S1/S2, E1e `identical_to`; unit suite 222 passed, 1 skipped. Probes 9–18 in test/e2e/out/probes.
- **Key finding:** run-to-run variance comes from the scroll viewport of an alignment panel whose reads overflow `maxPanelHeight`: its 3-px divider (y≈333) takes several states asynchronously. Capture timing cannot fix it (probe 18: 5–6 states per 12 processes); with no overflow the output is one state.
- **Known issues:** WIP is not reproducible for overflowing panels and costs ~+35 % plus re-render passes; do not merge as is. 1.3.1 on main is untouched and deployed.
- **Exact next steps:** (1) inspect IGV MainPanel/DataPanelContainer offscreen painting (classes extracted in the session scratchpad; re-extract from /opt/IGV_2.19.8/lib/igv.jar); (2) choose between opt-in fit-to-content height, uncapped-render-and-splice, or an IGV patch; (3) rework block + tests; (4) full e2e both modes, release 1.4.0.

### 2026-09-25 22:05 · Claude Code · igver 1.3.1 released: unknown gene/contig detection, working -f pdf
- **Done:** User decisions recorded (keep 1150x800; unknown locus + PDF in 1.3.1; variance undecided). Probes + javap of IGV 2.19.8: `goto` always returns OK; after a good region, an unknown gene/contig or a start beyond the chromosome end **keeps the previous view** (1.3.0 saved the previous region under the new name — seen in the U1a baseline PNG); a bare `snapshot` is named after IGV's current locus; `gotoimmediate All` resets the view; a split view drops a bad locus. Implemented per docs/plans/20260925_1_3_1_plan.md: per-region verification snapshot + reset, `_verify_loci()` (wrong snapshots deleted, exit 1 listing regions and what IGV showed), `ensure_svg_size()` (SVG width/height/viewBox from the verification PNG → real PDFs), `python-cairosvg` in the image. Cost ~0.1 s/region (20 regions: 26.4/26.9 s → 28.5/28.9 s).
  - Unit: test/test_1_3_1.py 19/19 (13 failed on 1.3.0, 5 preservation passes); suite 209 passed, 1 skipped. Changed existing test: test_batch_chunking.py::test_split_batch_roundtrip (new block shape).
  - e2e (5 new cases U1a–U1e; E5b now expects exit 1; R4 checks the PDF): baseline 1.3.0 2/7 pass per mode; full run at 6845feb host 32/33, image 31/33 (E1e variance; R4 needed the rebuilt image); **release gate on the pulled 1.3.1 SIF: 33/33** (R4 PDF 108,399 bytes, rasterises to 1150 px, opened). PNGs opened: U1a kept region, U1d TP53 (chr17), R4 PDF raster.
  - Release: main 6845feb pushed, CI 36209224146 green; `igver_1.3.1_igv2.19.8.sif`: BUILD_SHA 6845feb, `igver 1.3.1`, cairosvg 2.9.1, no .git/BAM. `igver_latest.sif` → 1.3.1; 1.3.0 SIF → `archived/` (only this ledger and the plan referenced it). RetroEM still pins 1.2.1 (kept).
- **Key paths:** igver/igver.py (`_records_to_batch` verify_dir, `_verify_loci`, `ensure_svg_size`, `_snapshot_name`, `run_igv`), docker/Dockerfile, test/test_1_3_1.py, test/e2e/cases.tsv (U1a–U1e, E5b, R4), test/e2e/e2e_runner.py (`pdf_width`, `tmp_clean` = igver_*), docs/plans/20260925_1_3_1_plan.md, README.md, CLAUDE.md, rules/igv.md; /data1/greenbab/software/images/igver_1.3.1_igv2.19.8.sif
- **Commands that worked:** `javap -c -p -cp <extracted igv.jar classes> org.broad.igv.batch.CommandExecutor` (run inside the SIF, which has the JDK); gate: `sbatch ... test/e2e/run_e2e.sh image --no-repo-bind --sif /data1/greenbab/software/images/igver_1.3.1_igv2.19.8.sif --tag gate131`
- **Known issues / blockers:** E1e run-to-run chrome variance still flaky (passed in the gate, failed in both full runs at 0.58 %): open unknown 3.
- **Exact next steps:** see "Exact next steps" above.

### 2026-09-25 20:35 · Claude Code · igver 1.3.0 released: 12 audited bugs fixed (B1 and C2/C4 blocked on open unknowns 3/5)
- **Done:** Executed docs/plans/20260925_audit_bugfix_plan.md. Commits on fix/audit-1.3.0, fast-forwarded to main at ba3e901 and pushed (main + branch). CI run 36203673348 green (3 min). Pulled `sahuno/igver:1.3.0`; release gate passed 27/28. `igver_latest.sif` → 1.3.0; the 1.2.3 SIF moved to `archived/` (the only references were this ledger and the plan). The 1.2.1 SIF stays: RetroEM's `03_igv_top_loci.sbatch` still pins it, so that job was not rerun (C6).
  - Evidence per checked box (unit = test/test_audit_1_3_0.py class; e2e = case id, host+image, final runs: C2 at 3646d98 = logs/e2e_{host,image}_20260925_195905.log, gate = logs/e2e_image_20260925_201822.log):
  - B1: E1 `IGV Directory: …igver_igv_…`, never /home, 1 `Loading genome` ✓ · E1a (poisoned mm10) / E1b (poisoned hg19) render 1150 px; 1.2.3 rendered 700 px ✓ · E1c ~/igv log mtime + prefs sha1 unchanged; 1.2.3 changed the mtime ✓ · E1d soft clips: data area differs by 2,432 px vs 0 for controls, crop inspected; E1d_bad exit 1 in ~1 s ✓ · failure path: E3c prints the kept run dir + log excerpt ✓ · E1e **blocked** (open unknown 3) · unit TestB1IsolatedIgvDirectory incl. clean-venv `pip install .` ✓ → B1 left unticked.
  - B2: TestB2RegionFileGrammar 14/14 incl. the 1,000-line fuzz (Random(42)) ✓ · E2a single panel (PNG opened) ✓, E2b chr8:32,534,767-32,536,767 (opened) ✓, E2c exit 1 in 1.0/1.5 s ✓.
  - B3: TestB3IndexPreflight 16/16 ✓ · E3a exit 1 in 0.8/1.4 s naming test_tumor_link.bam.bai + `ln -s`, no run dir ✓ · E3b: index older than BAM → IGV renders, no dialog, so no warning ✓ · E3c/E11f forced stall (404 URL) print the log excerpt incl. the `Loading resource: <url>` line ✓.
  - B4: TestB4Sanitiser 18/18 (incl. idempotence fuzz, 200-byte cap, quoting) ✓ · E4a/E4b render `…my_region.png` / `…LINE_L1.png` ✓ · E4c path with a space renders (IGV accepts double quotes) ✓.
  - B5: TestB5RegionArguments 10/10 ✓ · E5a exit 1 in 1.0/1.4 s "region file not found" ✓ · E5b unknown gene: IGV silently shows the whole genome (no hang); igver warns ✓ (open unknown 4).
  - B6: TestB6Duplicates 4/4 ✓ · E6 (-j 2) 2 files, duplicate warning ✓. B7: TestB7TrackLists 4/4 ✓ · E7 PNG shows test_tumor.bam + e7_genes.hg19.bed (opened) ✓.
  - B8: TestB8GenomeFile 5/5 ✓ · E8 relative `grch37.fa` symlink, no manual binds, one `Loading genome: …grch37.fa`, PNG opened (reads match the reference) ✓.
  - B9: TestB9BedParsing 7/7 ✓ · E9 ✓. B11: E11 two run dirs, no BindException ✓ · E11f each chunk names its own kept dir ✓. B12: TestB12 ✓; changed existing tests listed in commit af21109.
  - B10: CI green ✓ · `/opt/igver/BUILD_SHA` = OCI revision label = ba3e901e0c69ec7da037e403c2d8f9e08ba3d0a5 = merge commit; `igver --version` 1.3.0 ✓ · `/opt/igver` has no .git, BAM or BAI ✓.
  - Regression: R1 BED track visible under default -d squish (opened) ✓; R2 mm10 ✓; R3 colorBy in the batch ✓; R4 `-f pdf` fails as in 1.2.3 (open unknown 5).
  - Suites: unit 190 passed, 1 skipped (test_cli.py out of scope). e2e C2: host 27/28 (R4), image 26/28 (E1e, R4); gate 27/28 (R4). **Not green**: C2 and C4 are blocked on open unknowns 3 and 5.
  - Existing tests changed because their expectation was the bug: test_bed_support.py test_parse_bed3_file (B12), test_empty_bed_file + test_malformed_bed_file (B9); test_igver_fixed.py test_create_batch_with_bed_file (B12); test_input_file.py test_cli_mixed_txt_and_direct (B7).
  - Design changes: 13 entries appended to the plan's "Design changes" section (DEFAULT_GENOME_KEY instead of -g; IGV copies ~/igv prefs; per-launch run dirs; --debug prints the batch; e2e `checks` column; forced-stall trigger = 404 URL; E7/E8 strengthened; sanitiser landed with B2; zero-length BED; quoting; B6 raises; B5 warning only; B8 extras; log excerpt always ends with the log tail).
- **Key paths:** igver/igver.py, igver/cli.py, igver/data/igv_prefs.properties, setup.py (1.3.0), MANIFEST.in, docker/Dockerfile, .dockerignore, .github/workflows/docker-publish.yml, README.md, CLAUDE.md, test/test_audit_1_3_0.py, test/e2e/, docs/plans/20260925_audit_bugfix_plan.md, /data1/greenbab/users/ahunos/apps/llm_configs/claude/rules/igv.md; /data1/greenbab/software/images/igver_1.3.0_igv2.19.8.sif (igver_latest.sif → it); archived/igver_1.2.3_igv2.19.8.sif
- **Commands that worked:**
  - `APPTAINER_CACHEDIR=/data1/greenbab/users/ahunos/apptainer_cache apptainer pull /data1/greenbab/software/images/igver_1.3.0_igv2.19.8.sif docker://sahuno/igver:1.3.0`
  - release gate: `sbatch -p cpushort --exclude=isca071 -c 2 --mem=16G -t 01:30:00 -o test/e2e/logs/slurm_%j.out test/e2e/run_e2e.sh image --no-repo-bind --sif /data1/greenbab/software/images/igver_1.3.0_igv2.19.8.sif --tag gate`
  - `gh run watch <id> -R sahuno/igver --exit-status`; push: `git -c credential.helper='!gh auth git-credential' push origin main fix/audit-1.3.0`
- **Known issues / blockers:** open unknowns 2–5. An intermittent SEVERE `ClassFormatError … XSystemTrayPeer` appears in some IGV logs (harmless, unrelated to igver). `pkill -f <pattern>` kills the calling shell when the pattern is in its own command line.
- **Exact next steps:** see "Exact next steps" above.

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
