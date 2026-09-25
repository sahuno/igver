# IGVer

Conveniently take IGV snapshots of multiple BAM/CRAM files over multiple genomic regions.

> **This is [sahuno/igver](https://github.com/sahuno/igver), a fork of [shahcompbio/igver](https://github.com/shahcompbio/igver).**
> The methylation, parallel-rendering and PDF features documented below live in this fork.
> PyPI's `igver` (1.1) is upstream and does **not** have them — see [Installation](#installation).

**New in 1.3.0 (this fork)** — fixes for the 12 bugs of the 2026-09-25 audit. Behaviour changes:
- **Your `~/igv` no longer affects screenshots.** Every IGV process gets a fresh, run-scoped IGV directory
  (`igver_igv_*` under `$TMPDIR`, else the output directory) with igver's bundled preferences
  (`igver/data/igv_prefs.properties`: 1150×800 window, batch port off, downsampling on, soft clips off) and
  `DEFAULT_GENOME_KEY=<-g genome>`, so IGV loads only the requested genome, freshly from IGV's server — no
  stale cached genome JSONs, no personal display settings, no shared log or port under `-j`. It is deleted
  on success and kept on failure, and the error shows its log's SEVERE/ERROR lines (or its last lines).
- **`--igv-prefs FILE`**: extra IGV preferences, one `KEY=VALUE` per line (e.g. `SAM.SHOW_SOFT_CLIPPED=true`),
  applied after the template. A malformed line exits 1 before IGV starts.
- **Region text files have a grammar** (see [Region Files](#region-files)): only the *leading* `chr:start-end`
  tokens are loci; the rest of the line is the tag (spaces → `_`). A tag shaped like a locus (house locus IDs)
  stays a tag, BED-like lines are read as BED, and any other line exits 1 with `file:line` — it used to
  produce a hidden whole-genome `.tag.png` with exit 0.
- **Snapshot filenames are sanitised**: characters outside `[A-Za-z0-9._+=,-]` become `_` (BED names with
  spaces, `/`, `|`, `:` used to fail), no leading `.`, at most 200 bytes. See [Output File Naming](#output-file-naming).
- **BED coordinates**: `goto` now uses `start+1` (BED is 0-based, IGV 1-based); the filename keeps the BED
  coordinates. Tab-separated as before; a whitespace-separated BED is read with a warning; `.BED` and
  `.bed.gz` work; a bad line or an empty BED is an error naming the file (and line).
- **Pre-flight checks before IGV starts** (instead of a 2 × `--stall-timeout` hang): a missing BAM/CRAM/VCF.gz/BCF
  index (looked for beside the path as given — a symlinked BAM needs its index beside the link), a missing
  region file (`-r typo.bed` used to be treated as a locus), a reversed locus, a relative or unindexed FASTA
  for `-g`. Relative genome files are made absolute and their directories bind-mounted.
- Duplicate regions are rendered once (with a warning); every `.txt` item of `-i` is a track list (mixed
  with tracks too); paths with spaces are quoted; URL tracks (`https://`, `s3://` …) are passed through.
- `-r <gene name>` warns: IGV 2.19.8 silently snapshots the **whole genome** for a name (or contig) it does not know.
- The image is built from the commit being built (`/opt/igver/BUILD_SHA`), not from `main` HEAD.
- **Known issue**: `-f pdf` does not work with IGV 2.19.8 (also in 1.2.x): its SVGs carry no size, so the
  converted PDF is empty and igver exits 1. Use `-f svg` or PNG.

**New in 1.2.3 (this fork):**
- **Fixed**: `-d/--overlap-display` (default `squish`) is now applied to BAM/CRAM/SAM tracks by name. It used to be a bare IGV command that also squished the RefSeq gene track, which then filled the panel and hid every BED/annotation track below it. Annotation tracks now keep IGV's default (collapsed) layout.

**New in 1.2.2 (this fork):**
- Refreshed the bundled genome definitions for hg19, hg38, mm10, mm39 and rn6 from igv.org; their sequence/annotation URLs pointed at retired S3 buckets (HTTP 403/404), which makes IGV hang on an error dialog in headless mode
- (igver ≤ 1.2.3 only; 1.3.0 does not read `~/igv`) If screenshots hang right after `Loading genome: ~/igv/genomes/<genome>.json`, your *cached* copy is stale: `curl -sf https://igv.org/genomes/json/<genome>.json -o ~/igv/genomes/<genome>.json`

**New in 1.2.1 (this fork):**
- IGV 2.19.8 in the container (from 2.19.5); `/opt/IGV_2.19.5` is kept as a symlink so igver ≤ 1.2.0 still works against `:latest`

**New in 1.2.0 (this fork):**
- `--methylation` / `--meth` — one-flag base-modification coloring for ONT/PacBio data
- `--color-by` — set any IGV `colorBy` value, validated against IGV's enum (IGV silently ignores typos, so igver hard-fails instead)
- `-j` / `--jobs` — render regions in parallel across several IGV processes
- `--stall-timeout` — kill and retry an IGV process that stops producing snapshots (headless error dialogs)
- `-f pdf` now actually writes PDFs; retries re-render only the *missing* regions
- `--version` flag
- **Fixed**: genome aliases (`-g GRCh38` → `hg38`) never resolved in any earlier version — the alias table was loaded from a YAML key that does not exist, so every alias was passed to IGV verbatim

**From 0.2.0:**
- IGV 2.19.5 (from 2.17.4)
- BED region input (BED3/BED6)
- Multiple output formats (PNG, SVG, PDF)

**Container versions:**
- `sahuno/igver:latest` — most recent (recommended)
- `sahuno/igver:1.3.0` — igver 1.3.0 with IGV 2.19.8; run-scoped IGV preferences, pre-flight checks, region grammar
- `sahuno/igver:1.2.3` — igver 1.2.3 with IGV 2.19.8; `-d` no longer hides BED tracks
- `sahuno/igver:1.2.2` — igver 1.2.2 with IGV 2.19.8 and refreshed genome definitions
- `sahuno/igver:1.2.1` — igver 1.2.1 with IGV 2.19.8
- `sahuno/igver:1.2.0` — igver 1.2.0 with IGV 2.19.5

## Table of Contents
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [CLI](#cli)
  - [CLI Options Reference](#cli-options-reference)
  - [Environment Variables](#environment-variables)
  - [Python API](#python-api)
- [Supported File Formats](#supported-file-formats)
- [Output File Naming](#output-file-naming)
- [Examples](#examples)
- [Advanced Usage](#advanced-usage)
  - [DNA Methylation Visualization (ONT/PacBio)](#dna-methylation-visualization-ontpacbio)
  - [Haplotagged Reads](#working-with-haplotagged-reads)
  - [Parallel Rendering and Stalled IGV Processes](#parallel-rendering-and-stalled-igv-processes)
  - [Batch Processing](#batch-processing-multiple-samples)
- [Supported Genomes](#supported-genomes)
- [Lessons Learned & Common Pitfalls](#lessons-learned--common-pitfalls)
- [Performance Tips](#performance-tips)
- [Troubleshooting](#troubleshooting)
- [License](#license)
- [Authors](#authors)

## Features
- Generate high-resolution IGV screenshots programmatically
- Multiple BAM/CRAM files and multiple genomic regions per run
- BED region input (BED3/BED6) and legacy region text files
- Base-modification (methylation) and haplotype coloring
- Parallel rendering across IGV processes, with a stall watchdog and per-region retry
- Runs IGV in a container for reproducibility
- Python API for embedding in analysis scripts

## Requirements
- Python 3.9+ (3.6–3.8 work with the `importlib_resources` backport declared in `setup.py`)
- Singularity/Apptainer or Docker
- Python packages: matplotlib, Pillow, PyYAML (installed automatically); `cairosvg` for `-f pdf`

## Installation

### Option 1: Container (Recommended)
```bash
# Docker
docker pull sahuno/igver:latest

# Singularity/Apptainer
singularity pull docker://sahuno/igver:latest
```

### Option 2: From this fork
```bash
pip install "git+https://github.com/sahuno/igver.git"

# with PDF output support
pip install "igver[pdf] @ git+https://github.com/sahuno/igver.git"
```

> **Do not use `pip install igver` if you need the flags documented here.** PyPI serves upstream
> `igver 1.1`, which has no `--color-by`, `--methylation`, `-j/--jobs`, `--stall-timeout`, or
> `--version`, and still carries the genome-alias bug. Check what you have with `igver --version`
> (it reports the *installed distribution* version, so reinstall after pulling new commits).

**Note**: A local install still requires Singularity/Docker to run IGV itself.

### Container Usage Important Notes

**Docker**: works automatically — the container environment is auto-detected.

**Singularity**: you must pass `--no-singularity`, otherwise igver tries to launch a second
container inside the first:
```bash
singularity exec docker://sahuno/igver:latest igver ... --no-singularity
```

## Quick Start

```bash
# Using Docker
docker run --rm \
  -v $(pwd):/data \
  -v $(pwd)/output:/output \
  sahuno/igver:latest \
  igver -i /data/sample.bam -r "chr1:1000000-2000000" -o /output/

# Using Singularity (IMPORTANT: use --no-singularity flag)
singularity exec \
  -B $(pwd):/data \
  -B $(pwd)/output:/output \
  docker://sahuno/igver:latest \
  igver -i /data/sample.bam -r "chr1:1000000-2000000" -o /output/ --no-singularity

# Using local installation (requires Singularity)
igver -i sample.bam -r "chr1:1000000-2000000" -o output/

# Using BED file for regions
igver -i sample.bam -r regions.bed -o output/ --no-singularity
```

## Usage

### CLI

#### Basic Usage
```bash
igver \
  -i test/test_tumor.bam test/test_normal.bam \
  -r "chr1:1000000-2000000" \
  -o ./screenshots
```

All tracks passed to `-i` are loaded into the **same** screenshot, stacked as panels — one image
per region, not one per BAM. Paths must be space-separated; a comma-separated string is treated as
a single filename.

#### Using BED Files
```bash
# BED3 (chr, start, end)
igver -i sample.bam -r regions.bed -o ./screenshots

# BED4+ — the 4th column (name) is appended to the output filename
igver -i sample.bam -r regions_with_names.bed -o ./screenshots
```

#### Multiple Regions
```bash
# Two loci side by side in ONE image (split-screen)
igver -i sample.bam -r "chr1:1000-2000 chr2:3000-4000" -o ./screenshots

# Two separate images
igver -i sample.bam -r "chr1:1000-2000" "chr2:3000-4000" -o ./screenshots
```

### CLI Options Reference

| Flag | Description | Default |
|------|-------------|---------|
| `-i`, `--input` | Input BAM/CRAM/BEDPE/VCF/bigWig file(s) or URLs; every `.txt` item is a track list (one path per line), expanded in place | *required* |
| `-r`, `--regions` | Genomic regions (`chr1:100-200`), region file (`.txt`), or BED file (`.bed`, `.bed.gz`); an argument with a `/` or a file extension that does not exist is an error | *required* |
| `-o`, `--output` | Output directory for screenshots. When left at the default, `$TMPDIR` is used if set, else `/tmp` | `$TMPDIR` or `/tmp` |
| `-g`, `--genome` | IGV genome id (`hg38`), a supported alias (`GRCh38`), or a path (relative is fine) to a reference FASTA (needs `.fai`; `.gz` also `.gzi`), `.genome` or `.json` | `hg19` |
| `--dpi` | DPI resolution for output images | `300` |
| `--igv-dir` | Path to the IGV installation inside the container (IGV's writable prefs/cache/log directory is separate and created per run) | `/opt/IGV_2.19.8` |
| `--igv-prefs` | File of extra IGV preferences, one `KEY=VALUE` per line, applied after igver's bundled template | *none* |
| `-p`, `--max-panel-height` | Maximum pixel height per track panel | `200` |
| `-d`, `--overlap-display` | Read display mode: `expand`, `collapse`, or `squish` | `squish` |
| `-c`, `--igv-config` | File of additional IGV **batch commands** injected before each snapshot (not `KEY=VALUE` properties) | *none* |
| `-f`, `--format` | Output format: `png`, `svg`, or `pdf` (pdf requires `cairosvg`) | `png` |
| `--color-by` | IGV `colorBy` value injected before each snapshot, e.g. `BASE_MODIFICATION` or `'TAG HP'`; unknown values are rejected with exit code 1 | *none* |
| `--methylation`, `--meth` | Shortcut for `--color-by BASE_MODIFICATION` | `false` |
| `-j`, `--jobs` | Number of IGV processes run in parallel; regions are split into this many chunks (each process is its own JVM) | `1` |
| `--stall-timeout` | Kill IGV if no new snapshot appears for this many seconds, then retry the missing regions once; guards against IGV blocking on a headless error dialog. `0` disables | `600` |
| `--singularity-image` | Singularity/Docker image path | `docker://sahuno/igver:latest` |
| `--singularity-args` | Additional Singularity arguments; input/output/TMPDIR binds are added automatically (see [pitfall 3](#3-bind-mounting-data-directories)) | `-B /home` |
| `--no-singularity` | Run IGV directly without the Singularity wrapper (**required** when igver itself runs inside a container) | `false` |
| `--debug` | Enable debug logging (prints the batch script, the IGV command, each run's IGV directory and IGV's console output) | `false` |
| `--version` | Print the igver version and exit | — |

**Notes on `--igv-config`**: the file may contain any valid
[IGV batch command](https://igv.org/doc/desktop/#UserGuide/tools/batch/). Its contents are injected
after each `goto` and before each `snapshot`. If `--color-by` is also given, the `colorBy` line is
emitted first, then the config file. igver warns if a line looks like `KEY=VALUE` properties syntax,
which the IGV batch interpreter silently ignores. Example commands:
- `colorBy BASE_MODIFICATION` — color reads by DNA methylation (ONT/PacBio)
- `colorBy TAG HP` — color reads by haplotype tag
- `group TAG HP` — group reads by haplotype
- `sort READNAME` — sort reads by name

### Environment Variables

| Variable | Effect |
|----------|--------|
| `IGVER_IMAGE` | Overrides `--singularity-image` (useful for pinning a local `.sif` cluster-wide) |
| `IGVER_IN_CONTAINER=1` | Forces container mode — igver will not wrap IGV in Singularity |
| `IGVER_NO_SINGULARITY=1` | Same as above; equivalent to always passing `--no-singularity` |
| `TMPDIR` | Used as the output directory when `-o` is left at its default, and always bind-mounted into the container |

Container mode is also auto-detected via `/.dockerenv`, `$SINGULARITY_CONTAINER`, and `/proc/1/cgroup`.

### Python API

#### Basic Example
```python
import igver

# Returns matplotlib figures (PNG output + load_figures=True, the defaults)
figures = igver.load_screenshots(
    paths=['tumor.bam', 'normal.bam'],
    regions=['chr1:1000000-2000000', 'chr2:3000000-4000000'],
    output_dir='./screenshots',
    genome='hg19'
)

for i, fig in enumerate(figures):
    fig.savefig(f'screenshot_{i}.png', dpi=300, bbox_inches='tight')
```

```python
# Returns file paths — no matplotlib figures held in memory.
# Prefer this for large region sets; it is what the CLI uses.
output_paths = igver.load_screenshots(
    paths=['ont.bam'],
    regions=['regions.bed'],
    output_dir='./screenshots',
    genome='hg38',
    color_by='BASE_MODIFICATION',
    jobs=4,
    load_figures=False,
)
```

#### API Reference
```python
igver.load_screenshots(
    paths,                     # list of input files (BAM/CRAM/VCF/BEDPE/bigWig)
    regions,                   # list of regions, or a path to a .bed / .txt region file
    output_dir='/tmp',         # '/tmp' resolves to $TMPDIR when that is set
    genome='hg19',             # IGV genome id, alias, or reference FASTA path
    igv_dir='/opt/IGV_2.19.8',
    overwrite=True,            # remove pre-existing outputs before rendering
    remove_png=True,           # delete image files after loading them into figures
    dpi=300,
    singularity_image='docker://sahuno/igver:latest',
    singularity_args='-B /home',
    debug=False,
    output_format='png',       # 'png' | 'svg' | 'pdf'
    use_singularity=None,      # None = auto-detect container environment
    load_figures=True,         # False returns paths instead of matplotlib figures
    jobs=1,                    # parallel IGV processes
    stall_timeout=600,         # seconds without a new snapshot before kill+retry
    **kwargs                   # tag, max_panel_height, overlap_display, igv_config, color_by
)
```

**Return value**: matplotlib `Figure` objects only when `output_format='png'` **and**
`load_figures=True`. Otherwise (SVG/PDF output, or `load_figures=False`) a list of output file
paths is returned.

```python
# Generate the IGV batch script without running IGV
batch_file, output_paths = igver.create_batch_script(
    paths=['sample.bam'],
    regions=['chr1:1000-2000'],
    output_dir='screenshots/',
    genome='hg38',
    color_by='BASE_MODIFICATION',
)

# Run a batch script yourself
igver.run_igv(batch_file, output_paths, use_singularity=False)
```

## Supported File Formats

### Input Files
- **BAM** (requires `<f>.bai`, `<stem>.bai` or `<f>.csi` beside the path as given; checked before IGV starts)
- **CRAM** (requires `<f>.crai` or `<stem>.crai`; pass the reference FASTA via `--genome`)
- **VCF.gz / BCF** (require `.tbi`/`.csi` / `.csi`)
- **URLs** (`https://`, `s3://`, …) are passed to IGV as is (no index check)
- **BEDPE** (structural variants)
- **VCF** (variant calls)
- **bigWig** (coverage tracks)
- **`.txt`** manifest: one track path per line, `#` comments and blank lines skipped, `~` expanded

### Region Files
- **BED3**: `chrom<TAB>start<TAB>end` (`.bed`, `.BED`, `.bed.gz`). Starts are 0-based: `chr1 100 200` is
  shown as `chr1:101-200`. A whitespace-separated BED is read with a warning; a line that is not
  `chrom start end` with integer coordinates, or a file with no regions, is an error naming file and line.
- **BED4/BED6**: a non-empty 4th column (name) is appended (sanitised) to the output filename; `track`/`browser`/`#` lines are skipped
- **Text** (any other extension), one image per line, whitespace-separated tokens:
  - the **leading** tokens of the form `contig:start-end` are the loci (several = one split-screen image, e.g.
    for SVs). The contig is everything before the *last* colon (`HLA-A*01:01:01:01:1-100` is one locus);
    coordinates may contain commas; start must be ≤ end.
  - everything from the first non-locus token on is the **tag**, joined with `_`
    (`chr1:1-2 my tag here` → tag `my_tag_here`; `chr1:1-2 chr1:1-2.L1.1.+` → tag `chr1_1-2.L1.1.+`).
  - a line without a leading locus is read as BED if it looks like BED (`chr1 100 200 name`, warned once
    per file); anything else (e.g. a bare `TP53`) is an error with `file:line`. `#` lines and blank lines are skipped.

### Output Formats
- **PNG** (default): raster
- **SVG**: vector, written directly by IGV
- **PDF**: IGV writes SVG, then igver converts it with `cairosvg` (`pip install cairosvg`).
  Via the CLI the intermediate `.svg` files are **kept** next to the `.pdf`s.
  **Currently broken with IGV 2.19.8** (1.2.x too): its SVGs have no width/height/viewBox, so cairosvg
  writes an empty PDF and igver exits 1; the image also lacks cairosvg. Use `-f svg`.

## Output File Naming

The extension follows `-f/--format` (`svg` for both `-f svg` and the intermediate of `-f pdf`):

- Single region: `chr1-1000000-2000000.png`
- BED with a name column: `chr1-1000000-2000000.gene_name.png`
- Split-screen region string: `chr1-1000-2000.chr2-3000-4000.png`
- Region text file with a tag: `chr1-1000000-2000000.translocation.png`

Colons become hyphens; spaces between regions become dots. A BED name column takes precedence over
an explicit `tag`. All tracks given to `-i` share one image per region.

- BED regions keep their **BED coordinates** in the filename (`chr1 100 200` → `chr1-100-200.png`,
  shown as `chr1:101-200`), so downstream scripts can match files to BED lines.
- Loci are normalised: `chr1:1,000-2,000` → `chr1-1000-2000`.
- Every name part (BED name, text-file tag, `tag`, the region itself) is sanitised: characters outside
  `[A-Za-z0-9._+=,-]` become `_`, runs of `_` collapse, leading `.`/`_` are dropped, and the whole
  filename is capped at 200 bytes (the tag is truncated first). Examples: `my region` → `my_region`,
  `LINE/L1` → `LINE_L1`, `chr1:1-2.L1|3.-` → `chr1_1-2.L1_3.-`, `.hidden` → `hidden`.
- Two lines with the same locus and the same resulting filename are rendered once (with a warning);
  two different loci that would share a filename are an error.

## Examples

### Example 1: Simple Screenshot
```bash
igver -i sample.bam -r "chr1:1000000-2000000" -o ./
```
Creates: `./chr1-1000000-2000000.png`

### Example 2: Structural Variant Visualization
```bash
# Region text file for a translocation: two loci + a tag, on one line
printf 'chr8:128750000-128760000\tchr14:106330000-106340000\ttranslocation\n' > sv_regions.txt

igver \
  -i tumor.bam normal.bam \
  -r sv_regions.txt \
  -o ./sv_screenshots
```
Creates: `./sv_screenshots/chr8-128750000-128760000.chr14-106330000-106340000.translocation.png`

### Example 3: Different Output Formats
```bash
# SVG (vector)
igver -i sample.bam -r "chr1:1000000-2000000" -f svg -o ./

# PDF (requires cairosvg; leaves the intermediate .svg next to the .pdf)
pip install cairosvg
igver -i sample.bam -r "chr1:1000000-2000000" -f pdf -o ./
```

### Example 4: Custom IGV Batch Commands
```bash
cat > custom_prefs.txt << EOF
colorBy TAG HP
sort READNAME
group TAG RG
EOF

igver -i sample.bam -r regions.bed -c custom_prefs.txt -o ./screenshots
```

## Advanced Usage

### DNA Methylation Visualization (ONT/PacBio)

BAM/CRAM files from ONT (dorado/guppy) or PacBio carry base-modification tags (`MM`/`ML`) for
5mCG, 5hmCG, 6mA, etc. Use `--methylation` (alias `--meth`):

```bash
# Avoid stale bind variables that can cause mount failures
unset SINGULARITY_BIND APPTAINER_BIND 2>/dev/null || true

singularity exec -B /data1 docker://sahuno/igver:latest \
  igver \
    -i sample_modBaseCalls_dedup_sorted.bam \
    -r regions.bed \
    -o ./IGV_hg38_methylation \
    -g hg38 \
    --methylation \
    --dpi 600 \
    -d expand \
    -p 1000 \
    --no-singularity
```

`--methylation` is exactly `--color-by BASE_MODIFICATION`. Use `--color-by` directly for the
two-color variant, or `-c` when you need several batch commands:

```bash
igver ... --color-by BASE_MODIFICATION_2COLOR      # equivalent to a one-line -c file
printf 'colorBy BASE_MODIFICATION\ngroup TAG HP\n' > meth_hp.txt && igver ... -c meth_hp.txt
```

**CRAM files** work identically to BAM — pass the reference FASTA via `--genome`:
```bash
igver -i sample.cram -r regions.bed --genome /path/to/reference.fna --methylation ...
```

**Color interpretation**:
- **Red** = methylated CpG (5mC)
- **Blue** = unmethylated CpG
- Color intensity reflects the modification probability (from the `ML` tag)

**Requirements**: the input BAM/CRAM must contain `MM`/`ML` tags from a methylation-aware
basecaller (dorado, guppy, etc.).

**Valid `colorBy` values for base modifications**:

| Value | Effect |
|-------|--------|
| `BASE_MODIFICATION` | Color by all base modifications (5mC, 6mA, ...) |
| `BASE_MODIFICATION_2COLOR` | Two-color mode (red = methylated, blue = unmethylated) |

> **Warning**: `colorBy BASE_MODIFICATION_5MC` is **not valid** — IGV silently ignores it. Only the
> two values above are accepted for `colorBy`; the `_5MC` suffix works solely with the `preference`
> command (`preference SAM.COLOR_BY BASE_MODIFICATION_5MC`). `--color-by` validates against IGV's
> enum and exits 1 on an unknown value, but a bad value inside a `-c` file still reaches IGV unchecked.

**Quick diagnostic**: methylation-colored screenshots are roughly **2x the file size** of gray ones
at the same locus (~80KB vs ~35KB at 600 DPI) — a fast way to confirm coloring worked.

### Working with Haplotagged Reads
```bash
cat > haplotype_view.batch << EOF
group TAG HP
colorBy TAG HP
sort READNAME
EOF

igver \
  -i haplotagged.bam \
  -r regions.bed \
  -c haplotype_view.batch \
  -p 500 \
  -o ./haplotype_screenshots

# Coloring only (no grouping) needs no config file — quote the two-word value:
igver -i haplotagged.bam -r regions.bed --color-by 'TAG HP' -o ./haplotype_screenshots
```

### Parallel Rendering and Stalled IGV Processes

For large region sets, split the work across IGV processes with `-j/--jobs`:

```bash
igver -i sample.bam -r 1483_L1_elements.bed -j 8 -o ./screenshots
```

- Regions are split into `jobs` contiguous chunks; each chunk gets its own batch script, IGV
  process and JVM — **budget memory per job**, not per run.
- `--stall-timeout` (default 600s) kills an IGV process that has produced no new snapshot for that
  long, then retries the regions still missing. This is aimed at IGV blocking on an error dialog
  that nobody can dismiss in headless mode. `--stall-timeout 0` disables the watchdog.
- Rendering is attempted at most **2 iterations**; the second pass re-renders only the snapshots
  that are still missing, not the whole batch.
- If snapshots are still missing after that, igver raises and **keeps the batch script** for the
  missing regions so you can run it by hand, and **keeps that process's IGV directory**
  (`igver_igv_*`); the error message names it and quotes its `igv0.log` (SEVERE/ERROR lines, or the last
  lines — IGV logs nothing for some errors, e.g. a 404 track URL, but the last line names the resource).
  With `-j`, every failed chunk is reported with its own directory.
- Each process has its own IGV directory and the batch port is disabled, so parallel JVMs no longer
  share a log or race for port 60151.

### Batch Processing Multiple Samples
```python
import glob
import os

import igver

bam_files = glob.glob("samples/*.bam")
regions = ["chr1:1000000-2000000", "chr2:3000000-4000000"]

for bam in bam_files:
    sample_name = os.path.basename(bam).replace('.bam', '')
    output_paths = igver.load_screenshots(
        paths=[bam],
        regions=regions,
        output_dir=f'screenshots/{sample_name}',
        load_figures=False,  # avoids holding a matplotlib figure per region
    )
```

## Supported Genomes

Pass any IGV genome id directly (`hg19`, `hg38`, `mm10`, `mm39`, `hs1`, ...), a path to a reference
FASTA/`.genome` file, or one of the aliases below, which igver resolves before handing the value to
IGV. Anything not in the table is passed through unchanged.

| Organism | Alias | IGV genome |
|----------|-------|------------|
| Human | `GRCh37`, `hg37`, `b37` | hg19 |
| Human | `GRCh38` | hg38 |
| Human | `hg38_1kg`, `hs1` | hg38_1kg, hs1 |
| Mouse | `GRCm38` | mm10 |
| Mouse | `GRCm39` | mm39 |
| Rat | `Rnor_6.0` | rn6 |
| Dog | `CanFam3.1`, `CanFam5` | canFam3, canFam5 |
| Chicken | `GRCg6a` | galGal6 |
| Zebrafish | `GRCz10`, `GRCz11` | danRer10, danRer11 |
| Fly | `BDGP6`, `BDGP5` | dm6, dm3 |
| Worm | `WBcel235` | ce11 |
| Yeast | `R64-1-1` | sacCer3 |
| Arabidopsis | `TAIR10` | tair10 |
| Cow | `UMD3.1`, `ARS-UCD1.2` | bosTau8, bosTau9 |
| Primates | `Mmul_8.0.1`, `Pan_tro_3.0`, `Ggor_gorGor4`, `Ggor_gorGor6`, `NHGRI_mPanPan1` | macFas5, panTro4, gorGor4, gorGor6, panPan2 |

The authoritative list is `igver/data/genome_map.yaml`.

> Alias resolution was broken in every release up to and including upstream 1.1 (the alias table was
> read from a nonexistent `aliases:` YAML key). If you are on an older build, pass the IGV genome id
> directly.

## Lessons Learned & Common Pitfalls

### 1. Chromosome Naming Mismatch (`chr` prefix)

The most common issue. BAMs aligned to Broad's `Homo_sapiens_assembly38.fasta` use `chr1`, `chr2`;
many tools (L1EM, some BED generators) emit `1`, `2`. IGV's `hg38` expects the `chr` prefix.

**Symptom**: empty screenshots or "region not found" errors.

**Fix**:
```bash
awk 'BEGIN{OFS="\t"} { if ($1 !~ /^chr/) $1 = "chr" $1; print }' regions.bed \
  > regions.hg38.chrPrefix.bed
```

**Prevention**: check that `samtools view -H file.bam | grep @SQ | head` and your region file agree.

### 2. Nested Container Execution

When igver itself runs inside a Singularity container, pass `--no-singularity`, or it will try to
start a second container inside the first:

```bash
# Correct
singularity exec docker://sahuno/igver:latest igver ... --no-singularity

# Wrong — nested container error
singularity exec docker://sahuno/igver:latest igver ...
```

Docker is auto-detected and needs no flag. `IGVER_NO_SINGULARITY=1` has the same effect as the flag.

### 3. Bind-Mounting Data Directories

igver adds bind mounts automatically for the directory of **every input track** (both the absolute
and the resolved-symlink path, so symlinked BAMs work), the **output directory**, and `$TMPDIR`.
Those you do not need to pass yourself.

You still need `--singularity-args`/`-B` for paths igver cannot see in `-i`/`-o`:
- the reference FASTA passed via `--genome`
- the `--igv-config` file, if it lives outside the input/output trees
- index files stored away from their BAM/CRAM

```bash
igver -i sample.cram -r regions.bed -g /data1/references/hg38.fa \
  --singularity-args "-B /home -B /data1/references" -o ./screenshots
```

Also `unset SINGULARITY_BIND APPTAINER_BIND` first — stale bind variables from a login node cause
mount failures on compute nodes.

### 4. Large Region Sets (>500 regions)

Hundreds or thousands of regions (e.g. 1,483 L1 elements) take a long time — IGV navigates and
renders each one.

**Recommendations**:
- Use `-j/--jobs` to render chunks in parallel (each job is a separate JVM — size memory accordingly)
- Keep `--stall-timeout` enabled so one wedged IGV process cannot hang the whole run
- Run under `screen`/`tmux` or submit as a SLURM job
- Use `load_figures=False` in the Python API (the CLI already does) to avoid one matplotlib figure per region

### 5. Display Mode for Long Reads (ONT/PacBio)

Use `-d expand` with a large panel height (`-p 1000` or more) so individual reads — and their
methylation coloring — are visible. The default `squish` compresses reads and hides that detail.

```bash
igver -i ont_reads.bam -r regions.bed -d expand -p 1000 --dpi 600 -o ./screenshots
```

## Performance Tips

- **Pre-pull containers** (or pin a local `.sif` with `IGVER_IMAGE`) so runs do not pay the pull cost
- **Use absolute paths** for inputs — they are what gets written into the IGV batch script
- **Parallelize with `-j`** rather than launching several igver processes by hand
- **Skip figure loading** (`load_figures=False`) for large runs
- **Budget memory per job**: every `-j` chunk starts its own JVM

## Troubleshooting

### Container Issues
- **`singularity: command not found` inside a container**: pass `--no-singularity`
  ```bash
  singularity exec docker://sahuno/igver:latest igver ... --no-singularity
  ```
- **Permission denied / file not found inside the container**: bind the directory holding the
  reference or config file (input, output and `$TMPDIR` are bound automatically)
  ```bash
  singularity exec -B /data,/home docker://sahuno/igver:latest igver ... --no-singularity
  ```
- **Image not found**: `singularity pull docker://sahuno/igver:latest`

### Common Errors
- **`Failed to generate all PNG files after 2 iterations`**: igver keeps the batch script for the
  regions that failed and that run's IGV directory (`igver_igv_*`) — both paths and the IGV log's
  errors are in the error message. Rerun with `--debug` to see IGV's console output.
- **Whole-genome view instead of the region**: IGV did not know the gene or contig name. Check
  chromosome naming (`chr1` vs `1`) against the BAM header and the genome.
- **No screenshots generated**:
  - Check chromosome naming (`chr1` vs `1`)
  - Check output directory permissions
- **Run hangs, no new files**: IGV is probably blocked on a headless error dialog — that is what
  `--stall-timeout` is for; lower it (e.g. `--stall-timeout 120`) to fail faster.
- **`--color-by` rejected**: the value is validated against IGV's `colorBy` enum. The error lists
  every accepted value. Quote two-word values: `--color-by 'TAG HP'`.
- **`igv-config line looks like properties format` warning**: IGV batch scripts take commands
  (`colorBy BASE_MODIFICATION`), not `KEY=VALUE`. Use `preference KEY VALUE` for a preference.

### IGV Display Issues
- Screenshots are rendered on a fixed 1920x1080 virtual display (`xvfb-run --server-args="-screen 0
  1920x1080x24"` in `run_igv`). Increase `--dpi` for higher-resolution output and `-p` for taller
  read panels; the virtual screen width is not currently configurable from the CLI.

## Testing

```bash
# Unit tests that do not need IGV
pytest test/test_genome_aliases.py test/test_bed_support.py -q

# Full suite (requires Singularity and the igver image)
pytest test/test_cli.py
```

## License

MIT License - see [LICENSE](LICENSE) file for details

## Authors

- Seongmin Choi ([@soymintc](https://github.com/soymintc)) — original author
- Samuel Ahuno ([@sahuno](https://github.com/sahuno)) — this fork (methylation/colorBy flags,
  parallel rendering, stall watchdog, PDF output, genome-alias fix)
- Contributors welcome!

## Citation

If you use IGVer in your research, please cite:
```
Choi, S. (2024). IGVer: Automated IGV Screenshot Generation for Genomics.
GitHub: https://github.com/shahcompbio/igver
```

## Contributing

Contributions are welcome! Please open a Pull Request against
[sahuno/igver](https://github.com/sahuno/igver); changes intended for upstream go to
[shahcompbio/igver](https://github.com/shahcompbio/igver).
