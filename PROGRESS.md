---
project: igver
status: active
owner: Samuel Ahuno
team: greenbab lab igver users
next_action: Once the 1.2.1 CI build is green, pull the new SIF and run a smoke-test screenshot
blockers: none
updated: 2026-09-25
shared_copy: none
---

# igver (sahuno fork)

Headless IGV screenshot tool (fork of shahcompbio/igver). This fork carries the
methylation, `--color-by`, parallel-rendering, PDF and genome-alias fixes. The
container `sahuno/igver` is built by GitHub Actions on every push to `main`.

## Exact next steps

1. Watch the "Build and Push Docker Image" run for the 1.2.1 commit: `gh run list -R sahuno/igver -L 1`
2. Pull a fresh SIF to a new file, e.g. `igver_1.2.1_igv2.19.8.sif` (don't overwrite the shared `/data1/greenbab/software/images/igver_latest.sif`)
3. Smoke-test: `apptainer exec <sif> ls /opt/IGV_2.19.8/igv.sh /opt/IGV_2.19.5/igv.sh`, `igver --version`, one screenshot of `test/test_tumor.bam`
4. Decide whether to replace `igver_latest.sif` with the new image

## Open unknowns

| # | Question | Owner | Decide by | Status |
|---|---|---|---|---|
| 1 | Swap shared `igver_latest.sif` to the IGV 2.19.8 build? | Samuel Ahuno | 2026-10-09 | open |

## Decisions

- 2026-09-25 · Did not merge or cherry-pick upstream `renov` (4a3329e, "fix PIL imports in Dockerfile") · main already installs the Python deps, has the TMPDIR/`igver.cli` test fixes, and clones the fork; `renov` branches from 2025-03 and conflicts. Took only its IGV 2.19.8 bump · by Samuel Ahuno
- 2026-09-25 · Bumped igver to 1.2.1 with IGV 2.19.8 · CI tags the image with the setup.py version, so leaving it at 1.2.0 would have overwritten the `sahuno/igver:1.2.0` tag · by Samuel Ahuno

## Log

### 2026-09-25 · Claude Code · IGV 2.19.5 → 2.19.8, igver 1.2.1, conda env reinstalled
- **Done:** Confirmed `apps/igver` is the most recent clone (matches origin/main; 19 ahead of upstream/main; `projects/IGVAgent/igver` is an older clone). Reinstalled the `igver` conda env as an editable install (was a non-editable 0.3) and added cairosvg. Bumped the Dockerfile to IGV 2.19.8, and the `igv_dir` defaults in cli.py/igver.py to `/opt/IGV_2.19.8`. Added a `/opt/IGV_2.19.5` symlink in the image so igver ≤ 1.2.0 still works with `:latest`. setup.py → 1.2.1; docs and test_igv_version.py updated. 32 unit tests pass.
- **Key paths:** /data1/greenbab/users/ahunos/apps/igver/docker/Dockerfile, igver/cli.py, igver/igver.py, setup.py, test/test_igv_version.py, README.md, DOCKER_USAGE.md, CLAUDE.md
- **Commands that worked:**
  - `/home/ahunos/miniforge3/envs/igver/bin/pip install -e . && /home/ahunos/miniforge3/envs/igver/bin/pip install cairosvg`
  - `/home/ahunos/miniforge3/envs/igver/bin/python -m pytest test/test_igv_version.py test/test_genome_aliases.py test/test_bed_support.py -q`
- **Known issues / blockers:** Until the new image is in use, host igver 1.2.1 (both conda envs are editable) points at `/opt/IGV_2.19.8`, which doesn't exist in older SIFs such as `igver_latest.sif`. For those, pass `--igv-dir /opt/IGV_2.19.5`, or run inside the SIF with `--no-singularity`.
- **Exact next steps:** see "Exact next steps" above.
