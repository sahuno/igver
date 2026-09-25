# igver audit bug-fix plan (target release 1.3.0)

Author: Samuel Ahuno (plan drafted with Claude Code), 2026-09-25
Status: NOT STARTED. The executing agent updates the checklist in §7 and `PROGRESS.md` as it works.

This plan is written for an autonomous Claude Code session that starts with **no memory** of the
session that produced it. Everything needed is here or linked. Read the whole plan before touching code.

---

## 0. Ground rules (non-negotiable)

1. **Evaluations first.** Phase A writes every acceptance test and every end-to-end (e2e) case in §4
   *before* any fix. Run them against the current code and record which ones fail. A test that
   passes on the unfixed code is not testing the bug: fix the test, not the code.
2. **No shortcuts.** Forbidden: `xfail`/`skip` on an acceptance test, weakening an assertion to
   make it pass, deleting or loosening an existing test, catching and ignoring exceptions so a test
   goes green, special-casing test inputs in product code, marking a done-item checked without
   running its verification. If a done criterion cannot be met, record it under `## Open unknowns`
   in `PROGRESS.md` with the evidence, leave the item unchecked, and move on. **Never claim done.**
3. **Evidence for every check.** Each checked box in §7 gets a one-line proof in the `PROGRESS.md`
   log: test name(s), e2e case id, or command output. Visual claims need the PNG to have been
   opened with the Read tool.
4. **Loop** (§6) until every item in §7 is checked or explicitly blocked, the full suite is green,
   e2e is green in both run modes, and the release (§5) is done.
5. **Do not modify the user's `~/igv`.** Poisoned-environment tests use bind-mount overlays (§3.4).
6. **Work on branch `fix/audit-1.3.0`.** Pushing to `main` triggers an image build; merge once at the end.
7. Keep code style consistent with `igver/igver.py`: docstrings with Parameters/Returns/Example,
   `[WARNING]`/`[ERROR]` prefixes, no new dependencies unless unavoidable.

---

## 1. Background: what igver does

`igver` writes an IGV batch script (`create_batch_script` in `igver/igver.py`) and runs IGV headless
under `xvfb-run` (`run_igv`), either inside the Singularity image (`docker://sahuno/igver:*`, IGV at
`/opt/IGV_2.19.8`) or wrapped by igver on the host. `cli.py` parses arguments. Regions come from
`chr:start-end` strings, `.bed` files (`_parse_bed_file`) or text files (`_parse_region_file`).
A stall watchdog (`_run_until_stalled`) kills IGV when no new snapshot appears for
`--stall-timeout` seconds (default 600), then retries only the missing regions once.

Key facts established on 2026-09-25 (see `PROGRESS.md` log entries of that date):
- IGV 2.19.8 CLI supports `--igvDirectory <dir>` ("Defaults to <user home>/igv"), `--preferences/-o
  <file>` and `--port/-p`. If the directory is not writable it **falls back to `~/igv`** — this is
  why igver's current `--igvDirectory /opt/IGV_2.19.8` (read-only in the SIF) is silently ignored.
  The IGV log line `IGV Directory: <path>` shows which directory was used.
  `DirectoryManager` also references `IGV_DIR_USERPREF` / `checkDotIgvDirectory` (a user preference
  stored outside `~/igv`, e.g. Java Preferences under `~/.java`) — verify it cannot override your choice.
- IGV blocks forever on a modal error dialog in headless mode. Any unhandled error = hang.
- A bare `squish`/`expand` batch command applies to every track (fixed in 1.2.3 by
  `_display_commands`); do not regress this (`test/test_display_mode.py`).

---

## 2. The bugs (ranked) — design and definition of done

Severity: **S1** silent wrong output or non-reproducible output; **S2** long hang or failure with a
misleading message; **S3** minor/cosmetic. Evidence: "repro" = reproduced with real IGV on
2026-09-25; "code" = confirmed by reading.

### B1 (S1, repro) — Screenshots depend on the user's personal `~/igv`
**Problem.** IGV uses `~/igv` (prefs, genome cache, logs) for every run. Personal prefs change the
output (`SAM.DOWNSAMPLE_READS`, `SAM.SHOW_SOFT_CLIPPED`, `IGV.Bounds` sets image width, per-data-type
sections like `##THIRD_GEN` `SAM.COLOR_BY=...`); stale cached genome JSONs (`~/igv/genomes/*.json`
pointing at retired S3 buckets) made mm10 runs hang on 2026-09-25.

**Design.**
- Each IGV process gets a fresh, writable, run-scoped IGV directory created by igver
  (`tempfile.mkdtemp(prefix="igver_igv_", dir=<TMPDIR or output_dir>)`), passed as
  `--igvDirectory <dir>`. It must be reachable inside the container (TMPDIR is already bound;
  verify for both run modes).
- igver writes a controlled `prefs.properties` into that directory from a bundled template
  `igver/data/igv_prefs.properties` (packaged via `package_data`). Template contents must be explicit
  and documented. Minimum: `IGV.Bounds` (fixed width/height, pick and document), `PORT_ENABLED=false`
  (avoids the port-60151 clash under `-j`), `SAM.DOWNSAMPLE_READS=true` (IGV default; say so),
  `SAM.SHOW_SOFT_CLIPPED=false`. `IGV.Bounds` defaults to the current de-facto `0,0,1150,800` so
  existing lab figures keep their 1150-px width; choosing a different size is the user's decision
  (record it as an open unknown, do not pick one).
- Avoid the extra default-genome load (today IGV loads hg38 first, then the requested genome, and
  fetches an hg38 RefSeq index that 404s): pass `-g <genome>` on the IGV command line in addition to
  the batch `genome` line. Confirm with the `Loading genome:` lines in the run's IGV log (exactly one,
  for the requested genome). If `-g` does not achieve it, try `DEFAULT_GENOME_KEY=<genome>` in the
  generated prefs and record which worked.
- New CLI option `--igv-prefs FILE`: extra `KEY=VALUE` lines appended after the template (user
  override, explicit and reproducible). Reject lines that are not `KEY=VALUE`.
- On success delete the run directory. On failure keep it and print its path plus the last 20
  `SEVERE`/`ERROR` lines of its `igv0.log` in the igver error message (this also fixes B11's
  misleading log hint).
- Remove the dead `--igvDirectory {igv_dir}` usage; `--igv-dir` keeps meaning "IGV install dir".
- Genome JSONs are then fetched fresh from IGV's genome server on every run (small files). Measure the
  added startup time and record it; if it exceeds 10 s per run, record it as an open unknown but do
  not reintroduce the shared cache.

**Done when.**
- [ ] Log of every run contains `IGV Directory: <igver run dir>`, never `/home/<user>/igv` (e2e E1, both modes).
- [ ] With a poisoned `~/igv` overlay (§3.4: dead-URL `mm10.json`, `IGV.Bounds=0,0,700,500`,
      `SAM.SHOW_SOFT_CLIPPED=true`), 1.2.3 hangs or renders at 700 px wide (negative control recorded), and
      the fixed code renders mm10 successfully with the template width (e2e E1a/E1b).
- [ ] Real `~/igv/igv0.log` mtime and `~/igv/prefs.properties` checksum are unchanged by a run (E1c).
- [ ] `--igv-prefs` with `SAM.SHOW_SOFT_CLIPPED=true` changes the rendering (visible soft clips on the
      test BAM; spot-checked PNG) and a malformed line exits 1 before IGV starts (unit + E1d).
- [ ] Failure path keeps the run dir and prints SEVERE lines (E3 output contains the log excerpt).
- [ ] Two identical runs of the same input produce byte-identical PNGs or, if IGV output is not
      deterministic, identical dimensions and a pixel difference below 0.5% (measure and record) (E1e).
- [ ] Unit tests: template is packaged and loadable after `pip install .` into a clean venv; the
      generated IGV command contains `--igvDirectory <tmp>`; `--igv-prefs` parsing positive/negative.

### B2 (S1, repro) — Text region files silently produce wrong screenshots
**Problem.** `_parse_region_file` treats any token with exactly one `:` and one `-` as a locus, in
any position. A line with no locus emits `goto ` (empty) and snapshot `.<tag>.png` (hidden file,
whole-genome view, exit 0). A tag shaped like a locus (house locus ID
`chr1:3014747-3021072.L1MdF_I.1.+`) is added as a second locus → split screen with a garbage panel,
exit 0. Multi-word tags keep only the last word.

**Design.** Define and document the grammar (README + docstring):
- A line is whitespace-split into tokens. **Leading** tokens that fully match the locus regex
  `^(.+):([0-9][0-9,]*)-([0-9][0-9,]*)$` (contig = everything before the **last** colon, so hg38 alt
  contigs such as `HLA-A*01:01:01:01` in `Homo_sapiens_assembly38.fasta` are valid) are loci (one or
  more; several = IGV split view, intended for SVs). The "leading tokens only" rule is what stops
  locus-shaped tags from being read as loci.
  Everything after the first non-locus token is the tag, joined with `_`.
- start ≤ end required (after removing commas); otherwise error with file:line.
- A line with zero leading loci: if it is BED-like (≥3 fields, fields 2–3 integers) parse it as a
  BED record (warn once per file: "BED-like lines in <file>; consider a .bed extension"); otherwise
  **error** with file:line and the offending text. Never emit an empty `goto`.
- An output name can never start with `.` (see B4 sanitiser).

**Done when.**
- [ ] Unit tests (write first, must fail on current code): locus-ID tag with `+` stays a tag;
      multi-word tag preserved (`my_tag_here`); `chr1 100 200 regionA` in `.txt` parses as a BED
      region; `TP53` alone errors with line number; `chr1:200-100` errors; comma coordinates work;
      two leading loci + tag → split view + tag (legacy SV format still works: the existing
      `test/regions.txt` style); tag containing `:` and `-` in non-leading position stays a tag;
      `HLA-A*01:01:01:01:1-100` parses as one valid locus with contig `HLA-A*01:01:01:01`.
- [ ] No code path can produce `goto ` with an empty argument (property test: fuzz 1,000 random
      lines through the parser — each either raises `ValueError` with a line number or yields
      non-empty loci; use `random.Random(42)`).
- [ ] E2E E2a: the `+`-strand locus-ID file renders one panel (PNG opened and confirmed single panel)
      with the tag in the filename. E2b: the BED-like `.txt` renders the right locus, visible filename.
      E2c: a file with a bad line exits 1 in < 5 s without starting IGV.

### B3 (S2, repro) — Missing BAM/CRAM index hangs for 2 × stall-timeout
**Problem.** IGV shows an error dialog; igver's watchdog kills it twice (20 min at the default), then
fails with a message that does not mention the index.

**Design.** Pre-flight check in `cli.py` before IGV starts, for local (non-URL) tracks:
`.bam` needs `<f>.bai`, `<stem>.bai` or `<f>.csi`; `.cram` needs `<f>.crai` or `<stem>.crai`;
`.vcf.gz`/`.bcf` need `.tbi` or `.csi`. Missing → exit 1 listing every missing index and the command
to create it (`samtools index`, `tabix -p vcf`). **Look next to the path as given, not its
realpath**: IGV does the same. The 2026-09-25 probe used a symlinked BAM whose target had a `.bai`,
and IGV still hung. If the index exists only beside the realpath, say so in the error and suggest
symlinking the index next to the link. Also investigate: **index older than data file** —
make a temp copy of `test/test_tumor.bam` + index, `touch` the BAM so it is newer, run IGV and see
whether IGV raises a (hanging) dialog. If it does: warn (not error) in pre-flight and document. Record
the finding either way.
Add to the stall message: the tail of the run's IGV log (from B1).

**Done when.**
- [ ] Unit tests for each index naming convention (positive: each accepted name; negative: none
      present; symlinked BAM whose index sits only beside the target → error that mentions the target's index).
- [ ] E2E E3a: BAM symlink without index exits 1 in < 5 s, message names the missing index path, no
      IGV process started (no `igver_igv_*` run dir created).
- [ ] E3b (index-older investigation) result recorded in PROGRESS with evidence; behaviour matches the finding.
- [ ] Forced stall (e.g. `--stall-timeout 20` with a region on a contig IGV rejects, or another
      dialog trigger found) prints the IGV log excerpt.

### B4 (S2, repro) — BED names with spaces or `/` never produce a snapshot
**Problem.** IGV splits batch arguments on whitespace (`snapshot a b.png` → "Unknown region: b.png");
`/` creates a subdirectory path that does not exist. Both fail after retries with a generic error.
House locus IDs also contain `:` and `|`, which are invalid on Windows/OneDrive where figures get
copied.

**Design.** One sanitiser for every user-derived filename component (BED name, text-file tag,
`tag` argument): replace any character outside `[A-Za-z0-9._+=,-]` with `_`, collapse runs of `_`,
strip leading `.`/`_`, cap the full filename at 200 bytes (truncate the tag, keep the extension).
The region part keeps its existing `chr-start-end` form. Document the mapping in the README.
Also: paths passed to `load`, `snapshotDirectory` and `genome` may contain spaces — test whether IGV
batch accepts double-quoted arguments. If yes, quote them; if no, fail early with a clear message.

**Done when.**
- [ ] Unit tests: `my region` → `my_region`; `LINE/L1` → `LINE_L1`; `chr1:1-2.L1|3.-` →
      `chr1_1-2.L1_3.-`; `.hidden` → `hidden`; 300-char name truncated to ≤ 200-byte filename;
      unicode name → sanitised ASCII; the sanitiser is idempotent.
- [ ] E2E E4a/E4b: BED names with a space and with `/` render, with the expected sanitised filenames.
- [ ] E4c: an input BAM path containing a space either renders (quoting works) or fails in < 5 s
      with a clear message; the finding is recorded.

### B5 (S2, repro) — A typo'd region file path is treated as a locus
**Problem.** `-r regins.bed` (missing file) becomes `goto regins.bed`; the snapshot name contains the
path, so IGV cannot write it; the error does not say "file not found".

**Design.** In `_get_paths_and_regions` (or the CLI): a region argument that contains `/`, or ends in
`.bed`, `.bed.gz`, `.txt`, `.tsv` or `.csv` (case-insensitive), and does not exist → exit 1:
"region file not found: <path>". Otherwise a non-file region string must be a locus
(`chr:start-end`, split view allowed with spaces) or a single token without `/` (IGV feature search,
e.g. a gene name). Investigate what IGV does with an unknown gene name (`-r NOTAGENE123`, short
stall timeout): if it hangs, document it and make the stall message say "IGV could not find locus
'<x>'" when the IGV log shows that.

**Done when.**
- [ ] Unit tests: missing `.bed`/`.txt`/`.BED`/path-with-slash → error; `TP53` accepted;
      `chr1:1-100 chr2:5-10` accepted; `chr1:100-1` rejected.
- [ ] E2E E5a: `-r typo.bed` exits 1 in < 5 s with "region file not found". E5b: unknown gene
      behaviour recorded, message improved if applicable.

### B6 (S3, code) — Duplicate snapshot names overwrite silently
**Design.** After all regions are parsed, drop exact duplicate (same loci + same filename) blocks with
one warning listing them. Same filename with different content is impossible by construction; assert
that and raise if it ever happens.
**Done when.**
- [ ] Unit: BED with a duplicated line → one block + warning; duplicates across two `-r` files → one block.
- [ ] E2E E6 with `-j 2`: expected file count equals unique regions; no errors.

### B7 (S3, code) — A `.txt` track list only works as the sole `-i` argument
**Design.** Expand every `-i` item ending in `.txt` (case-insensitive) in place, preserving order;
mixed lists and several list files work. Keep existing semantics otherwise (comments, blank lines,
`~` expansion, relative paths resolved against the current directory as today — do not change that).
**Done when.**
- [ ] Unit: `-i list.txt extra.bam` → list contents then `extra.bam`; two lists; missing list → error.
- [ ] E2E E7: mixed `-i tracks.txt other.bed` renders both tracks (PNG confirms both track names).

### B8 (S3, code) — `-g` with a relative FASTA path fails; its directory is not bound
**Design.** If `--genome` names an existing local file (`.fa`, `.fasta`, `.fna`, `.genome`, `.json`,
optionally `.gz`), convert to an absolute path before writing the batch, and add its directory (and
the realpath's directory) to the Singularity binds. For FASTA, require an index (`.fai`; for `.gz`
also `.gzi`); missing → exit 1 before IGV starts.
**Done when.**
- [ ] Unit: relative FASTA → absolute path in batch; bind list contains its directory; missing `.fai` → error.
- [ ] E2E E8: create symlinks `test/e2e/fixtures/grch37.fa -> /data1/greenbab/database/human_GRCh37/GRCh37-lite.fa`
      and `grch37.fa.fai -> .../GRCh37-lite.fa.fai` (both exist; contigs have no `chr`, matching
      `test/test_tumor.bam`). Passing `-g grch37.fa` as a **relative** path from `test/e2e/fixtures/`
      renders `8:32534767-32536767` in host-wrapper mode with no manual `--singularity-args`. Because
      the FASTA is a symlink into `/data1/greenbab/database`, this also exercises the realpath bind.
      (Do not use a sliced FASTA: renaming a slice's contig shifts coordinates off the reads.)

### B9 (S3, code) — A space-separated BED silently yields zero regions
**Design.** In `_parse_bed_file`: split on tabs; if a non-header line has < 3 tab fields but ≥ 3
whitespace fields, parse on whitespace and warn once per file. Any other unparseable line → error
with file:line. Zero regions after parsing → error naming the file. Accept `.bed` case-insensitively
and `.bed.gz` (read with `gzip`).
**Done when.**
- [ ] Unit: space-separated BED parses (with warning); `chr1\tabc\t200` errors with line number;
      header/`track`/`browser`/`#` lines skipped; `.BED` and `.bed.gz` work; empty BED errors.
- [ ] E2E E9: space-separated BED renders the expected files.

### B10 (S3, code) — The image installs `main` HEAD instead of the commit being built
**Problem.** `docker/Dockerfile` runs `git clone https://github.com/sahuno/igver.git`, so an image
built later (release event, `workflow_dispatch`) can contain newer code than its version tag says.

**Design.** Build from the repo checkout: change the CI `context` to the repo root (`file:
docker/Dockerfile`), `COPY` the package (`setup.py`, `igver/`, `requirements.txt`, `README.md`) into
`/opt/igver`, install from that copy, keep the `/opt/igver/igver.py` compatibility wrapper, fix the
`ADD json/...` paths for the new context, and add a `.dockerignore` (exclude `.git`, `test/`, `docs/`,
`*.bam`/`*.bai`/`*.cram`, `igver_agent/`, `igver-mcp/`, `igver_final_test/`, `CLAUDE/`, `.claude/`,
and any hidden scratch directories). Record the commit SHA in the image (build-arg `GIT_SHA` →
`LABEL org.opencontainers.image.revision` and `/opt/igver/BUILD_SHA`).
**Done when.**
- [ ] CI run for the merge commit is green.
- [ ] `apptainer exec <new sif> cat /opt/igver/BUILD_SHA` equals the merge commit SHA, and
      `igver --version` equals `setup.py`'s version.
- [ ] The image contains no `.git` directory and no test BAMs (`apptainer exec <sif> ls -a /opt/igver`).

### B11 (S3, repro) — `-j` processes share `~/igv` (log rotation, port clash)
Fixed by B1's per-process run directory and `PORT_ENABLED=false`.
**Done when.**
- [ ] E2E E11 (`-j 2`): two distinct run dirs appear in the debug output; neither IGV log contains
      `BindException`; on a forced failure each chunk's message points at its own log.

### B12 (S3, code) — BED start passed to `goto` without +1
**Design.** `goto chrom:{start+1}-{end}` for BED records (0-based half-open → 1-based closed).
Filenames keep the original BED coordinates (downstream scripts match on them); document that.
**Done when.**
- [ ] Unit: BED `chr1 100 200` → `goto chr1:101-200`, filename `chr1-100-200...`.
- [ ] Existing BED tests updated only where they asserted the old off-by-one `goto` (justify each
      change in the commit message).

---

## 3. Environment and gotchas (read before running anything)

### 3.1 Paths and tools
- Repo: `/data1/greenbab/users/ahunos/apps/igver` (remote `origin` = github.com/sahuno/igver, HTTPS).
- Python: `/home/ahunos/miniforge3/envs/igver/bin/python` (editable install of the repo). Reinstall
  after a version bump: `/home/ahunos/miniforge3/envs/igver/bin/pip install -e .`. The login shell's
  default env cannot import igver.
- Apptainer: `/home/ahunos/miniforge3/envs/snakemake/bin/apptainer` (not on PATH on compute nodes).
  Always `unset APPTAINER_BIND SINGULARITY_BIND`; set
  `APPTAINER_CACHEDIR=/data1/greenbab/users/ahunos/apptainer_cache` for pulls.
- Current image: `/data1/greenbab/software/images/igver_latest.sif` → `igver_1.2.3_igv2.19.8.sif`.
  (`igver_1.2.1_igv2.19.8.sif` must stay: RetroEM's `03_igv_top_loci.sbatch` names it.)
- Test data: `test/test_tumor.bam` (+ `.bai`), hg19, contigs **without** `chr` (use `8:32534767-32536767`).
  hg38 BAM with reads: `/data1/greenbab/projects/AluEM/MDA5_protection_paper/Beers2/labpipe_alu2000/ALN/beerssim_HG38.sorted.bam`
  at `chr17:61268000-61282000` (BCAS3). Reference paths: `/data1/greenbab/users/ahunos/apps/llm_configs/claude/profiles/databases/databases_config.yaml`.

### 3.2 Running IGV (compute)
- IGV must not run on the login node. For single quick checks: if `$SLURM_JOB_ID` is set, `srun`
  creates a step inside that (possibly interactive) allocation (`srun -n1 -c1 --mem=8G -t 00:30:00
  <script>`; `-c 2` is refused there); otherwise `srun -p cpushort --exclude=isca071 -n1 -c1
  --mem=8G -t 00:30:00 <script>`.
- **Full e2e runs: always `sbatch`, one job per run mode**, to `cpushort` (2 h wall limit) with
  `--exclude=isca071 -c 2 --mem=16G -t 01:30:00` and a log under `test/e2e/logs/`. Never run the
  full suite as a step of an interactive allocation: the step dies when that session ends. If one
  mode needs more than 1.5 h, split the cases across two jobs.
- Two run modes must both be tested:
  - **Host-wrapper mode** (new code writes the batch, IGV runs in the image):
    `/home/ahunos/miniforge3/envs/igver/bin/igver ... --singularity-image <sif>` with
    `PATH=/home/ahunos/miniforge3/envs/snakemake/bin:$PATH` so `singularity` resolves.
  - **In-image mode** with the working tree mounted over the image's copy:
    `apptainer exec --bind /data1/greenbab --bind <repo>:/opt/igver <sif> igver ... --no-singularity`.
    **Do not use `igver --version` to verify the bind**: it reads package metadata from the image's
    site-packages and keeps printing the image's version even when the bind works. The real check:
    `apptainer exec --bind <repo>:/opt/igver <sif> sha1sum /opt/igver/igver/igver.py` must equal
    `sha1sum <repo>/igver/igver.py`, and `apptainer exec ... python -c "import igver; print(igver.__file__)"`
    must print a path under `/opt/igver/`.
- Use short `--stall-timeout` (30–60 s) in error-path cases so a hang costs about 2 minutes, not 20.
- IGV needs outbound HTTPS (genome JSONs, RefSeq from UCSC).

### 3.3 Session hooks and tool rules
- A hook blocks any Bash command that mentions both a mouse and a human genome build (mm10/hg38 …)
  in the same command. Keep them in separate commands, or use the Write/Edit tools for such text.
- A hook blocks creating `.bed` files whose names lack a genome tag: name test BEDs like
  `case.hg19.bed`.
- `rm` with a variable path must use `"${VAR:?}"/...` or a literal absolute path.
- No `sleep`-and-poll chains: use `run_in_background` with an `until` loop, or the Monitor tool.
- `git push` hangs on a username prompt (no credential helper). Use
  `git -c credential.helper='!gh auth git-credential' push origin <branch>`.
- Commit messages end with the Co-Authored-By line from the session's system reminder.

### 3.4 Poisoned-environment overlay (B1 tests)
Build `test/e2e/fixtures/poisoned_igv/` with `prefs.properties` (`IGV.Bounds=0,0,700,500`,
`SAM.SHOW_SOFT_CLIPPED=true`, `SAM.DOWNSAMPLE_READS=false`) and `genomes/mm10.json` +
`genomes/hg19.json` copied from IGV's current definitions but with every URL replaced by
`https://s3.amazonaws.com/igv.broadinstitute.org/...` (returns 403). Overlay it on the real home
folder only inside the container: `apptainer exec --bind <fixture>:/home/ahunos/igv ...`
(in-image mode). For host-wrapper mode, pass the same bind in `--singularity-args`. Note that
igver's default `--singularity-args` is `-B /home`: verify that Apptainer honours a sub-path bind
(`fixture:/home/ahunos/igv`) on top of an already-bound `/home` by listing
`/home/ahunos/igv/prefs.properties` inside the container. If it does not, pass `--singularity-args`
**without** `-B /home` for these cases (bind `/data1/greenbab` plus the fixture) rather than calling
E1a untestable. The real `~/igv` is never touched; E1c verifies that.

---

## 4. Phase A — evaluations to write before any fix

### 4.1 Unit acceptance tests
Create `test/test_audit_1_3_0.py` (header: author Samuel Ahuno, date, one-line purpose) with one test
class per bug (B1–B12). **Structure rule:** the module must collect on the unfixed code. Import
only symbols that exist today at module top; import new symbols (e.g. a sanitiser, a prefs loader)
*inside* the test functions that use them, so a missing name fails that test alone instead of
breaking collection of the whole file. `pytest.importorskip` is not allowed (it skips). "Fails on
the unfixed code" includes `ImportError`/`AttributeError`/`SystemExit`, not only `AssertionError`.
Cover covering every unit bullet in §2 — both **positive** cases (input that must
work) and **negative/adversarial** cases (input that must be rejected, or must not be misread).
Adversarial inputs to include at minimum:
- Region text lines: `chr1:1-2 chr1:1-2.L1.1.+`; `chr1:1-2\tmy tag here`; `chr1\t100\t200\tx`;
  `TP53`; `chr1:200-100`; `chr1:1,000-2,000`; empty tag; a line with only whitespace; a CRLF line
  ending; a tab-only separator; `chrUn_JH584304:1-100`; `HLA-A*01:01:01:01:1-100` (one valid locus).
- BED: name with a space, `/`, `|`, `:`, leading `.`, 300 characters, unicode; space-separated
  lines; `track`/`browser`/`#chr` header lines; `.BED`; `.bed.gz`; empty file; non-integer coordinates.
- Tracks: BAM with `.bam.bai`, with `.bai`, with `.csi`, with none; CRAM with/without `.crai`;
  `.txt` list mixed with tracks; URL tracks skip the index check.
- Genome: relative FASTA with and without `.fai`; an alias (`GRCh38`) still maps to `hg38`.
- Prefs: `--igv-prefs` valid, malformed, empty file.
Run the file on the **unfixed** code and paste the pass/fail list into `PROGRESS.md`. Expected:
every test tied to a bug fails; tests of behaviour that must be preserved (legacy SV region lines,
aliases, display-mode targeting) pass. Investigate any surprise before continuing.

### 4.2 End-to-end harness
Create `test/e2e/run_e2e.sh` (bash, `set -uo pipefail`, logs to `test/e2e/logs/e2e_<timestamp>.log`)
and `test/e2e/cases.tsv` with columns
`case_id  mode(host|image|both)  args  expect_exit  expect_files  max_seconds  notes`.
The harness runs each case in a fresh output directory under `test/e2e/out/<case_id>/` and asserts:
exit code; the exact file list (`ls -A`, so hidden files count); elapsed time ≤ `max_seconds`;
optional grep patterns on stderr; for success cases PNG width/height via Pillow. It prints one
`PASS/FAIL case_id reason` line per case and a summary, and exits non-zero on any failure.
Cases (ids referenced in §2): E1, E1a, E1b, E1c, E1d, E1e, E2a, E2b, E2c, E3a, E3b, E4a, E4b, E4c,
E5a, E5b, E6, E7, E8, E9, E11, plus regression cases:
- R1 default `-d squish` with BAM + BED at hg38 CFTR (`chr7:117540000-117560000`): the BED track is
  visible (visual check) — guards the 1.2.3 fix.
- R2 mm10 RNA BAM render (`/data1/greenbab/projects/triplicates_epigenetics_diyva/RNA/rerun_RNASeq_11032025/ALN/R-0-1_MM38.sorted.bam`,
  `chr13:9830023-9840665`) succeeds — guards the genome-JSON fix.
- R3 `--methylation` still injects `colorBy BASE_MODIFICATION` (batch inspection).
- R4 `-f pdf` still writes a PDF and keeps the SVG.
Add `test/e2e/out/` and `test/e2e/logs/` to `.gitignore`. Run the harness on the **unfixed** code
(host mode with the current SIF) and record the baseline PASS/FAIL table in `PROGRESS.md`.

### 4.3 Baseline of the existing suite
`/home/ahunos/miniforge3/envs/igver/bin/python -m pytest test/ --ignore=test/archive --ignore=test/test_cli.py -q -p no:cacheprovider`
→ **88 passed, 1 skipped** on commit `062cedc` (2026-09-25). This must never regress except for
tests whose old expectation was the bug itself (B12 `goto` coordinates); list each such change.
`test/test_cli.py` is **out of scope**: it pins upstream's `docker://quay.io/soymintc/igver` image
and needs `singularity` on PATH. Do not fix it and do not count it as a regression.

---

## 5. Phase C — release (only after every §7 item is checked or blocked)

1. Bump `setup.py` to `1.3.0`; update the README ("New in 1.3.0" with every behaviour change: prefs
   isolation and `--igv-prefs`, the region-file grammar, sanitised filenames, the BED `goto` +1,
   pre-flight checks, `.bed.gz`), CLAUDE.md (architecture notes and the new gotchas), and
   `/data1/greenbab/users/ahunos/apps/llm_configs/claude/rules/igv.md` (replace the stale-cache
   workaround text with "fixed in 1.3.0; for ≤ 1.2.3 …").
2. Full unit suite green; e2e green in both modes against the working tree.
3. Merge `fix/audit-1.3.0` into `main` (fast-forward or merge commit), push, and watch CI
   (`gh run watch <id> -R sahuno/igver --exit-status`).
4. Pull `docker://sahuno/igver:1.3.0` to `/data1/greenbab/software/images/igver_1.3.0_igv2.19.8.sif`.
   Verify B10. Re-run the whole e2e suite in in-image mode **against the pulled SIF without the
   working-tree bind** — this is the release gate.
5. Repoint `igver_latest.sif` to the 1.3.0 SIF; move `igver_1.2.3_igv2.19.8.sif` to
   `/data1/greenbab/software/images/archived/` unless something references it
   (`grep -rl igver_1.2.3 /data1/greenbab/users/ahunos/apps` first).
6. Re-run the RetroEM screenshot job only if its sbatch no longer pins the 1.2.1 SIF; otherwise leave it.
7. Update `PROGRESS.md` (five-field entry) and push.

---

## 6. Execution loop (Phase B)

Order (dependencies first): **B1+B11 → B2+B9+B12 → B4+B6 → B3 → B5 → B7 → B8 → B10.**
For each item:
1. Confirm its acceptance tests and e2e cases exist and fail on the current code.
2. Implement the design in §2 (if the design turns out wrong, change it, and write the reason and the
   new design into this file under "Design changes" at the end — never silently).
3. Run the item's unit tests, then the full unit suite.
4. Run the item's e2e cases in both modes; open every PNG the item's done criteria mention.
5. Review your own diff (`git diff`) for dead code, missed call sites (e.g. all three region parsers),
   and docstrings.
6. Commit on `fix/audit-1.3.0` with a message that names the bug id and lists the evidence.
7. Tick the boxes in §7 and add a `PROGRESS.md` log entry with the evidence.
Then pick the next item. After the last item run the entire e2e suite in both modes once more
(fixes interact), then Phase C.

Stop only when: every box in §7 is checked (or blocked with evidence in Open unknowns), the full
unit suite and the full e2e suite pass in both modes, the release gate (§5 step 4) passes, and
`PROGRESS.md` is updated. The final message lists each bug with its status and evidence, every
design change, every blocked item, and anything that still needs the user's decision.

---

## 7. Checklist

Phase A
- [ ] A1 `test/test_audit_1_3_0.py` written; baseline pass/fail recorded
- [ ] A2 e2e harness + cases written; baseline table recorded
- [ ] A3 poisoned-environment fixture built (§3.4)

Phase B (tick each bug only when all of its "Done when" boxes in §2 are ticked)
- [ ] B1  [ ] B2  [ ] B3  [ ] B4  [ ] B5  [ ] B6
- [ ] B7  [ ] B8  [ ] B9  [ ] B10 [ ] B11 [ ] B12

Phase C
- [ ] C1 docs updated  [ ] C2 suites green both modes  [ ] C3 merged, CI green
- [ ] C4 release-gate e2e on pulled SIF  [ ] C5 `igver_latest.sif` repointed, old SIF archived
- [ ] C7 PROGRESS.md final entry pushed

## Design changes
(append here: date, item, what changed, why)
- 2026-09-25 · B1 · `-g <genome>` on the IGV command line does **not** stop IGV loading its default genome
  first (probe: two `Loading genome:` lines). `DEFAULT_GENOME_KEY=<genome>` in the run's prefs does (one
  line). igver writes `DEFAULT_GENOME_KEY` (taken from the batch `genome` line) and does not pass `-g`.
- 2026-09-25 · B1 · IGV **copies the user's `~/igv/prefs.properties`** into a fresh `--igvDirectory` that has
  none, and keeps a pre-written one. So the template must always be written before IGV starts (it is).
- 2026-09-25 · B1 · Each IGV *launch* (not each `run_igv` call) gets its own run dir: a retry deletes the
  failed attempt's dir after printing its log excerpt, so the kept dir always holds the last attempt's log.
- 2026-09-25 · B1/E1 · The `IGV Directory:` and `Loading genome:` lines are observed in the `--debug` output
  (IGV's console output, which `--debug` already prints), not in the deleted run dir. `--debug` now also
  prints the batch script (needed by R3 "batch inspection").
- 2026-09-25 · B11 · With `-j`, every failed chunk is reported (1.2.3 re-raised only the first), so each
  chunk's message names its own kept run dir.
- 2026-09-25 · A2 · `cases.tsv` has one extra column, `checks` (grep/nogrep/count/width/tmp_clean/
  home_untouched/rundirs/same_as/differs_from/overlay/setup/visual), documented in its header. The bash
  entry `run_e2e.sh` logs and calls `e2e_runner.py`, which does the Pillow/pixel checks. Outputs go to
  `test/e2e/out/<mode>/<case_id>/`. A kept `<uuid>.batch` is reported but excluded from the exact file list.
- 2026-09-25 · A2 · Forced-stall trigger (E3c, E11f): a corrupt BAM, an unknown file type and a stale index
  all render without a dialog; a 404 URL track (`https://igv.org/does/not/exist/x.bam`) and a dead-URL genome
  JSON both block IGV. The 404 URL is used because it also writes SEVERE lines to the log.
- 2026-09-25 · A2 · E7 and E8 passed on 1.2.3 by file list alone (E8's PNG was silently rendered against the
  personal default genome, every read a mismatch). Both now grep IGV's `Loading resource:`/`Loading genome:`
  lines from `--debug`.
- 2026-09-25 · B2/B4 · `sanitize_name` and the 200-byte filename cap landed with B2 (the B2 grammar's tag
  output is defined in sanitised form), before B4's remaining items (path quoting, bind quoting).
  The sanitiser is also applied to the region part (a no-op for normal contigs; turns `*` in
  `HLA-A*01:01:01:01` into `_`). Loci are normalised in `goto` and filenames (`chr1:1,000-2,000` →
  `chr1:1000-2000`, `chr1-1000-2000`), also for `-r` strings. A text-file line without its own tag now falls
  back to the `tag` argument (1.2.3 ignored it); the CLI has no `--tag`, so only the API sees this.
- 2026-09-25 · B9/B12 · A zero-length BED interval (`start == end`) becomes a 1-bp `goto start+1-start+1`.
