---
project: igver
status: active
owner: Samuel Ahuno
team: greenbab lab igver users
next_action: Decide whether to point the shared igver_latest.sif at the new 1.2.1 / IGV 2.19.8 image
blockers: none
updated: 2026-09-25
shared_copy: none
---

# igver (sahuno fork)

Headless IGV screenshot tool (fork of shahcompbio/igver). This fork carries the
methylation, `--color-by`, parallel-rendering, PDF and genome-alias fixes. The
container `sahuno/igver` is built by GitHub Actions on every push to `main`.

## Exact next steps

1. Decide whether to replace `/data1/greenbab/software/images/igver_latest.sif` with `igver_1.2.1_igv2.19.8.sif` (see Open unknowns #1)
2. Optional: add a stable `/opt/igv` symlink and default `igv_dir` to it, so the next IGV bump is a one-line Dockerfile change

## Open unknowns

| # | Question | Owner | Decide by | Status |
|---|---|---|---|---|
| 1 | Swap shared `igver_latest.sif` to the IGV 2.19.8 build? | Samuel Ahuno | 2026-10-09 | open |

## Decisions

- 2026-09-25 · Did not merge or cherry-pick upstream `renov` (4a3329e, "fix PIL imports in Dockerfile") · main already installs the Python deps, has the TMPDIR/`igver.cli` test fixes, and clones the fork; `renov` branches from 2025-03 and conflicts. Took only its IGV 2.19.8 bump · by Samuel Ahuno
- 2026-09-25 · Bumped igver to 1.2.1 with IGV 2.19.8 · CI tags the image with the setup.py version, so leaving it at 1.2.0 would have overwritten the `sahuno/igver:1.2.0` tag · by Samuel Ahuno

## Log

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
