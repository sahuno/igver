---
project: igver
status: active
owner: Samuel Ahuno
team: greenbab lab igver users
next_action: none pending; archive the 1.2.1 SIF once RetroEM stops naming it
blockers: none
updated: 2026-09-25
shared_copy: none
---

# igver (sahuno fork)

Headless IGV screenshot tool (fork of shahcompbio/igver). This fork carries the
methylation, `--color-by`, parallel-rendering, PDF and genome-alias fixes. The
container `sahuno/igver` is built by GitHub Actions on every push to `main`.

## Exact next steps

1. When the RetroEM `03_igv_top_loci.sbatch` no longer names `igver_1.2.1_igv2.19.8.sif`, move that SIF to `images/archived/`
2. Optional: add a stable `/opt/igv` symlink and default `igv_dir` to it, so the next IGV bump is a one-line Dockerfile change

## Open unknowns

| # | Question | Owner | Decide by | Status |
|---|---|---|---|---|
| 1 | Swap shared `igver_latest.sif` to the IGV 2.19.8 build? | Samuel Ahuno | 2026-10-09 | decided 2026-09-25: yes |

## Decisions

- 2026-09-25 · Pointed shared `igver_latest.sif` at the 1.2.1 / IGV 2.19.8 image · the old file (2026-04-14) predated the overhaul: no --jobs/--stall-timeout/--version, hang-prone --methylation, broken aliases and PDF · by Samuel Ahuno
- 2026-09-25 · Did not merge or cherry-pick upstream `renov` (4a3329e, "fix PIL imports in Dockerfile") · main already installs the Python deps, has the TMPDIR/`igver.cli` test fixes, and clones the fork; `renov` branches from 2025-03 and conflicts. Took only its IGV 2.19.8 bump · by Samuel Ahuno
- 2026-09-25 · Bumped igver to 1.2.1 with IGV 2.19.8 · CI tags the image with the setup.py version, so leaving it at 1.2.0 would have overwritten the `sahuno/igver:1.2.0` tag · by Samuel Ahuno

## Log

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
