# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

IGVer is a genomics visualization automation tool that generates IGV (Integrative Genomics Viewer) screenshots for multiple BAM files across multiple genomic regions. It's designed for bioinformatics workflows, particularly for visualizing genomic variants and structural variations.

## Key Commands

### Installation and Development
```bash
# Install in development mode
pip install -e .

# Install dependencies
pip install -r requirements.txt

# Unit tests that do not need IGV or a container
pytest test/test_genome_aliases.py test/test_bed_support.py -q

# Full CLI tests (requires Singularity + the igver image)
pytest test/test_cli.py

# Build distribution
python setup.py sdist bdist_wheel
```

**Test environment on iris**: the login shell's default conda env (`r-env`) has no
Pillow/matplotlib, so `import igver` fails there. Use
`/home/ahunos/miniforge3/envs/igver/bin/python -m pytest ...` instead.

**Repo remotes**: `origin` is the fork `https://github.com/sahuno/igver.git` (push here);
`upstream` is `https://github.com/shahcompbio/igver.git` with its push URL set to `DISABLED`
(no write access). Both are HTTPS because `ssh` is not in PATH on compute nodes.

### CLI Usage
```bash
# Basic usage
igver -i input.bam -r "chr1:1000-2000" -o output_dir

# Multiple BAM files and regions (space-separated, NOT comma-separated)
igver -i sample1.bam sample2.bam -r regions.txt -o screenshots/
# Note: BAM files must be space-separated. Comma-separated paths will be treated as a single filename

# Using a text file with list of tracks (one per line)
igver -i tracks.txt -r regions.txt -o screenshots/

# With custom genome and container
igver -i input.bam -r "chr1:1000-2000" -g hg38 --singularity-image /path/to/igver.sif

# ONT/PacBio methylation coloring (one flag; == --color-by BASE_MODIFICATION)
igver -i ont.bam -r regions.bed -g hg38 --methylation -d expand -p 1000 --dpi 600

# Any other IGV colorBy value (validated against IGV's enum; quote two-word values)
igver -i haplotagged.bam -r regions.bed --color-by 'TAG HP'

# Parallel rendering for large region sets (each job = its own JVM)
igver -i sample.bam -r many_regions.bed -j 8 --stall-timeout 300

# Output format and version
igver -i input.bam -r "chr1:1000-2000" -f pdf   # png (default) | svg | pdf
igver --version
```

#### Input File Format (.txt)
The `-i/--input` parameter now supports a `.txt` file containing paths to track files:
- One path per line
- Lines starting with `#` are treated as comments
- Empty lines are ignored
- Paths with `~` are expanded to home directory

Example `tracks.txt`:
```
# Sample tracks for analysis
/path/to/sample1.bam
/path/to/sample2.bam

# Additional tracks
~/data/sample3.bam
```

### Python API
```python
import igver

# Generate screenshots -> matplotlib figures (png + load_figures=True only)
figures = igver.load_screenshots(
    paths=['sample1.bam', 'sample2.bam'],
    regions=['chr1:1000-2000', 'chr2:3000-4000'],
    output_dir='screenshots/',
    genome='hg19'
)

# -> list of output paths instead (what the CLI uses; avoids a figure per region)
output_paths = igver.load_screenshots(
    paths=['sample1.bam'],
    regions=['regions.bed'],
    output_dir='screenshots/',
    genome='hg38',
    color_by='BASE_MODIFICATION',
    jobs=4,
    load_figures=False,
)

# Create batch script only
batch_file, png_paths = igver.create_batch_script(
    paths=['sample1.bam', 'sample2.bam'],
    regions=['chr1:1000-2000', 'chr2:3000-4000'],
    output_dir='screenshots/',
    genome='hg19'
)
```

**Return type**: `load_screenshots()` returns matplotlib figures only when
`output_format='png'` **and** `load_figures=True`; for SVG/PDF output or
`load_figures=False` it returns a list of file paths.

## Architecture

### Core Flow
1. **Input Processing** (`cli.py`): Parse BAM files and genomic regions
2. **Batch Script Generation** (`igver.py`): Create IGV batch commands
3. **Container Execution**: Run IGV in Singularity container with xvfb
4. **Output**: Screenshots saved as PNG files

### Key Components

**igver/igver.py**
- `load_screenshots()`: Main API entry point
- `create_batch_script()`: Generates IGV batch files
- `run_igv()`: Executes IGV via Singularity

**igver/cli.py**
- Command-line interface using argparse
- Handles file validation and argument parsing

### Container Architecture
- Uses Singularity containers for reproducibility
- Default image: `docker://sahuno/igver:latest`
- Runs IGV 2.19.8 in headless mode using xvfb

## Genomics-Specific Considerations

### Supported Genomes
- Human: hg19, hg38 (aliases GRCh37/hg37/b37, GRCh38), hs1, hg38_1kg
- Mouse: mm10, mm39 (aliases GRCm38, GRCm39)
- Many others (rat, dog, chicken, zebrafish, fly, worm, yeast, arabidopsis, cow, primates)
- Custom genomes via a `.genome` file or a reference FASTA path passed to `-g`
- Alias table: `igver/data/genome_map.yaml`, loaded by `_load_genome_mappings()` in `cli.py`.
  The mapping lives at the **top level** of that YAML; the loader also accepts a nested
  `aliases:` block. Anything not in the table is passed to IGV unchanged.

### File Format Support
- Primary: BAM files (requires .bai index)
- Additional: BEDPE, VCF, bigWig
- Regions: BED3/BED6 format (.bed files), text files (.txt), or chr:start-end notation
  - BED3: chromosome, start, end
  - BED6: chromosome, start, end, name, score, strand (name included in output)

### Structural Variation Visualization
The tool includes specialized settings for visualizing:
- Inversions
- Translocations
- Duplications
- Custom breakpoints

## Testing

Test files are in `test/` directory:
- `test_cli.py`: pytest-based CLI tests
- Sample BAM files with indices
- `regions.txt`: Example genomic regions
- IGV batch templates for different use cases

Run tests with: `pytest test/test_cli.py`

## Important Implementation Details

1. **Singularity Dependency**: The tool requires Singularity to be installed and accessible in PATH
2. **Display Handling**: Uses xvfb for headless operation - no X display required
3. **Output Naming**: Screenshots are named as:
   - Without tags: `{region_formatted}.png` (e.g., `chr1-1000-2000.png`)
   - With tags: `{region_formatted}.{tag}.png` (e.g., `chr1-1000-2000.test.png`)
   - Region formatting: colons become hyphens (`:` → `-`), spaces between regions become dots
   - A BED name column (4th field) is used in place of `tag`
   - The extension follows `-f/--format`; `-f pdf` makes IGV write `.svg` first, then converts
     with cairosvg and (via the CLI) keeps the `.svg` alongside the `.pdf`
   - Note: When multiple BAMs are loaded together, they appear in the same screenshot
4. **Genome Aliases**: `-g GRCh38` is mapped to `hg38` before the batch script is written.
   This was broken until 1.2.0 — the loader read a nonexistent `aliases:` YAML key and returned
   `{}`, so every alias reached IGV verbatim. Regression test: `test/test_genome_aliases.py`.
5. **Auto bind mounts**: `load_screenshots()` appends `-B` for each input track's directory
   (absolute **and** realpath, so symlinked BAMs work), the output directory, and `$TMPDIR`.
   Only the reference FASTA and an out-of-tree `--igv-config` still need manual binds.
6. **Output directory default**: `-o` defaults to `/tmp`, which is then replaced by `$TMPDIR`
   when that variable is set.
7. **Env overrides**: `IGVER_IMAGE` (container image), `IGVER_IN_CONTAINER=1` /
   `IGVER_NO_SINGULARITY=1` (skip the Singularity wrapper).
8. **IGV Preferences**: Customizes IGV display settings for genomics visualization

## Lessons Learned & Common Pitfalls

### Chromosome Naming Mismatch (chr prefix)
- **Problem**: BED files from tools like L1EM often use non-prefixed chromosome names (`1`, `10`) while BAMs aligned to Broad's `Homo_sapiens_assembly38.fasta` (GRCh38) use `chr1`, `chr10`. IGV's `hg38` genome also expects `chr` prefix.
- **Solution**: Preprocess BED files to add `chr` prefix before passing to igver:
  ```bash
  awk 'BEGIN{OFS="\t"} { if ($1 !~ /^chr/) $1 = "chr" $1; print }' input.bed > input_chrPrefix.bed
  ```
- **Tip**: Always check BAM header (`samtools view -H`) and BED file chromosome names match before running igver.

### DNA Methylation Visualization (ONT data)
- **Problem**: Default igver screenshots don't show base modification colors from ONT BAMs/CRAMs (5mCG/5hmCG from dorado basecalling).
- **Solution**: Pass `--methylation` (alias `--meth`), which is exactly
  `--color-by BASE_MODIFICATION`. Both inject the `colorBy` batch command before each snapshot
  via the `additional_pref` mechanism in `create_batch_script()`. Use `-c/--igv-config` only
  when several batch commands are needed (e.g. `colorBy` + `group TAG HP`); with both, the
  `colorBy` line is emitted first.
- **Validation**: `--color-by` is checked against `VALID_COLOR_BY_VALUES` in `cli.py` and exits 1
  on an unknown value. A bad value inside a `-c` file is still passed to IGV unchecked.
- **Critical**: `colorBy BASE_MODIFICATION_5MC` is **NOT valid** — IGV silently ignores it with no error. Only `BASE_MODIFICATION` and `BASE_MODIFICATION_2COLOR` are valid `colorBy` values. The `_5MC` suffix only works with the `preference` command (`preference SAM.COLOR_BY BASE_MODIFICATION_5MC`).
- **CRAM support**: Works identically to BAM. Pass the reference FASTA via `--genome /path/to/ref.fna`.
- **Colors**: Red = methylated CpG, Blue = unmethylated CpG. Intensity reflects modification probability (ML tag).
- **Quick check**: Colored screenshots are ~2x the file size of gray ones (~80KB vs ~35KB at 600 DPI).
- **Requires**: BAM/CRAM must contain MM/ML tags (produced by dorado, guppy, or similar basecallers).

### Stale Singularity Bind Variables
- Always `unset SINGULARITY_BIND APPTAINER_BIND` at the top of igver scripts. Stale bind variables from the login node can cause mount failures inside the container.

### Running Inside Singularity
- When calling igver via `singularity exec ... igver`, always pass `--no-singularity` to avoid nested containerization.
- Input track dirs, the output dir and `$TMPDIR` are bind-mounted automatically. Bind manually
  only what igver cannot infer: the reference FASTA for CRAM, an out-of-tree igv-config file, or
  indexes stored away from their BAM:
  ```bash
  singularity exec --bind /data1/collab001,/data1/greenbab docker://sahuno/igver:latest igver ... --no-singularity
  ```

### Display Mode Must Target Alignment Tracks
- A bare `squish`/`expand` batch command applies to **every** track. A squished or expanded
  annotation track (the genome's RefSeq track, BED files) grows to fill the panel and pushes
  the tracks below it out of the snapshot. Before 1.2.3 the default `-d squish` hid every
  BED track this way.
- `_display_commands()` in `igver.py` emits `<mode> <basename>` for each BAM/CRAM/SAM track
  only; `expand` (IGV's default for reads) emits nothing. Regression test: `test/test_display_mode.py`.
- The same applies to hand-written `-c/--igv-config` commands: name the track.

### Large Region Sets (>1000 regions)
- IGV batch scripts with many regions (e.g., 1483 L1 elements) can take a long time. Consider running via SLURM or in a `screen`/`tmux` session.
- Use `-j/--jobs` to split the regions across parallel IGV processes; each job is a separate JVM,
  so scale the memory request with the job count, not the run.
- The retry mechanism (up to 2 iterations) re-renders only the snapshots still missing, not the
  whole batch. `--stall-timeout` (default 600s) kills an IGV process that has stopped producing
  snapshots — the usual cause is IGV blocking on an error dialog that headless mode cannot dismiss.
- On failure igver keeps the batch script for the missing regions (path is in the error message);
  IGV's own errors are in `~/igv/igv0.log`.

### ssh Not Available in All Environments
- `git pull` via SSH may fail on compute nodes where `ssh` binary is not in PATH. Use HTTPS URLs as a workaround:
  ```bash
  git pull https://github.com/sahuno/igver.git main
  ```

## Future Agent Development Notes

For creating an agent to streamline genomics analysis:
1. The core `load_screenshots()` function can be wrapped for batch processing
2. Consider adding support for automated region detection from VCF files
3. The batch script generation is modular and can be extended for custom workflows
4. Container approach ensures reproducibility across different environments