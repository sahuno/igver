# IGVer

Conveniently take IGV snapshots of multiple BAM files over multiple genomic regions.

**New in v0.2.0:**
- Updated to IGV version 2.19.5 (from 2.17.4)
- Added support for BED format input files (BED3 and BED6)
- Improved region file parsing
- Added support for multiple output formats (PNG, SVG, PDF)

**Container Versions:**
- `sahuno/igver:latest` - Always the most recent version (recommended)
- `sahuno/igver:2.19.5` - Specific version with IGV 2.19.5
- Version tags available starting from 2.19.5

## Table of Contents
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [CLI](#cli)
  - [CLI Options Reference](#cli-options-reference)
  - [Python API](#python-api)
- [Supported File Formats](#supported-file-formats)
- [Output File Naming](#output-file-naming)
- [Examples](#examples)
- [Advanced Usage](#advanced-usage)
  - [DNA Methylation Visualization (ONT)](#dna-methylation-visualization-ont)
  - [Haplotagged Reads](#working-with-haplotagged-reads)
  - [Batch Processing](#batch-processing-multiple-samples)
- [Supported Genomes](#supported-genomes)
- [Lessons Learned & Common Pitfalls](#lessons-learned--common-pitfalls)
- [Performance Tips](#performance-tips)
- [Troubleshooting](#troubleshooting)
- [License](#license)
- [Authors](#authors)

## Features
- Generate high-resolution IGV screenshots programmatically
- Support for multiple BAM files and multiple genomic regions
- BED file support (BED3 and BED6 formats)
- Run IGV in a containerized environment for reproducibility
- Integrate with Python scripts using the API
- Customize IGV display preferences

## Requirements
- Python 3.7+
- Singularity/Apptainer or Docker
- For local installation: matplotlib, Pillow, PyYAML

## Installation

### Option 1: Using Container (Recommended)
```bash
# For Docker
docker pull sahuno/igver:latest

# For Singularity/Apptainer
singularity pull docker://sahuno/igver:latest
```

**Available versions:**
- `sahuno/igver:latest` - Always the most recent version (recommended)
- `sahuno/igver:2.19.5` - Specific version with IGV 2.19.5

### Option 2: Local Installation
```bash
pip install igver
```
**Note**: Local installation still requires Singularity to run IGV.

### Container Usage Important Notes

**Docker**: Works automatically - the container environment is auto-detected.

**Singularity**: You MUST use the `--no-singularity` flag to prevent nested container issues:
```bash
singularity exec docker://sahuno/igver:latest igver ... --no-singularity
```

This is because IGVer was originally designed to wrap IGV in a Singularity container, but when IGVer itself runs in a container, this creates a nested container problem.

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

**Important Note for Container Users**: When running IGVer inside a container (Docker or Singularity), you must use the `--no-singularity` flag with Singularity to prevent nested container execution. Docker automatically detects the container environment.

## Usage

### CLI

#### Basic Usage
```bash
igver \
  -i test/test_tumor.bam test/test_normal.bam \
  -r "chr1:1000000-2000000" \
  -o ./screenshots
```

#### Using BED Files
```bash
# BED3 format (chr, start, end)
igver \
  -i sample.bam \
  -r regions.bed \
  -o ./screenshots

# BED6 format (includes region names in output)
igver \
  -i sample.bam \
  -r regions_with_names.bed \
  -o ./screenshots
```

#### Multiple Regions
```bash
# Multiple regions in one panel
igver \
  -i sample.bam \
  -r "chr1:1000-2000 chr2:3000-4000" \
  -o ./screenshots

# Multiple separate regions
igver \
  -i sample.bam \
  -r "chr1:1000-2000" "chr2:3000-4000" \
  -o ./screenshots
```

### CLI Options Reference

| Flag | Description | Default |
|------|-------------|---------|
| `-i`, `--input` | Input BAM/BEDPE/VCF/bigWig file(s), or a `.txt` file with one path per line | *required* |
| `-r`, `--regions` | Genomic regions (`chr1:100-200`), region file (`.txt`), or BED file (`.bed`) | *required* |
| `-o`, `--output` | Output directory for screenshots | `/tmp` |
| `-g`, `--genome` | Reference genome (supports aliases, e.g. `GRCh38` maps to `hg38`) | `hg19` |
| `--dpi` | DPI resolution for output images | `300` |
| `-p`, `--max-panel-height` | Maximum pixel height per track panel | `200` |
| `-d`, `--overlap-display` | Read display mode: `expand`, `collapse`, or `squish` | `squish` |
| `-c`, `--igv-config` | Path to file with additional IGV batch commands injected before each snapshot | *none* |
| `-f`, `--format` | Output format: `png`, `svg`, or `pdf` (pdf requires `cairosvg`) | `png` |
| `--singularity-image` | Singularity/Docker image path | `docker://sahuno/igver:latest` |
| `--singularity-args` | Additional Singularity arguments (e.g. bind mounts) | `-B /home` |
| `--no-singularity` | Run IGV directly without Singularity wrapper (**required** when running inside a container) | `false` |
| `--debug` | Enable debug logging | `false` |

**Notes on `--igv-config`**: This file can contain any valid [IGV batch command](https://igv.org/doc/desktop/#UserGuide/tools/batch/). The contents are injected after each `goto` and before each `snapshot`, allowing per-region customization of the display. Example commands:
- `colorBy BASE_MODIFICATION` — color reads by DNA methylation (ONT/PacBio)
- `colorBy TAG HP` — color reads by haplotype tag
- `group TAG HP` — group reads by haplotype
- `sort READNAME` — sort reads by name

### Python API

#### Basic Example
```python
import igver

# Generate screenshots
figures = igver.load_screenshots(
    paths=['tumor.bam', 'normal.bam'],
    regions=['chr1:1000000-2000000', 'chr2:3000000-4000000'],
    output_dir='./screenshots',
    genome='hg19'
)

# Save figures
for i, fig in enumerate(figures):
    fig.savefig(f'screenshot_{i}.png', dpi=300, bbox_inches='tight')
```

#### API Reference
```python
igver.load_screenshots(
    paths,              # List of input files
    regions,            # List of regions or BED file
    output_dir='/tmp',  # Output directory
    genome='hg19',      # Reference genome
    igv_dir='/opt/IGV_2.19.5',
    overwrite=True,     # Overwrite existing files
    remove_png=True,    # Remove temporary PNGs
    dpi=300,            # Figure resolution
    singularity_image='docker://sahuno/igver:latest',
    **kwargs            # Additional IGV options
)
```

## Supported File Formats

### Input Files
- **BAM** files (requires .bai index files)
- **BEDPE** files (for structural variants)
- **VCF** files (variant calls)
- **bigWig** files (coverage tracks)

### Region Files
- **BED3**: `chromosome<TAB>start<TAB>end`
- **BED6**: `chromosome<TAB>start<TAB>end<TAB>name<TAB>score<TAB>strand`
- **Text**: Custom format with optional annotations

### Output Formats
- **PNG** (default): Raster format, best for publications
- **SVG**: Vector format, scalable without quality loss
- **PDF**: Converted from SVG, requires `cairosvg` (`pip install igver[pdf]`)

## Output File Naming

- Single region: `chr1-1000000-2000000.png`
- BED with name: `chr1-1000000-2000000.gene_name.png`
- Multiple regions: `chr1-1000-2000.chr2-3000-4000.png`
- With annotation: `chr1-1000000-2000000.annotation.png`

## Examples

### Example 1: Simple Screenshot
```bash
igver -i sample.bam -r "chr1:1000000-2000000" -o ./
```
Creates: `./chr1-1000000-2000000.png`

### Example 2: Structural Variant Visualization
```bash
# Create a regions file for a translocation
echo -e "chr8:128750000-128760000\tchr14:106330000-106340000\ttranslocation" > sv_regions.bed

igver \
  -i tumor.bam normal.bam \
  -r sv_regions.bed \
  -o ./sv_screenshots
```

### Example 3: Different Output Formats
```bash
# Generate SVG (vector format)
igver -i sample.bam -r "chr1:1000000-2000000" -f svg -o ./

# Generate PDF (requires cairosvg)
pip install igver[pdf]  # Install PDF support
igver -i sample.bam -r "chr1:1000000-2000000" -f pdf -o ./
```

### Example 4: Custom IGV Preferences
```bash
# Create custom preferences
cat > custom_prefs.txt << EOF
colorBy TAG HP
sort READNAME
group TAG RG
EOF

igver \
  -i sample.bam \
  -r regions.bed \
  -c custom_prefs.txt \
  -o ./screenshots
```

## Advanced Usage

### DNA Methylation Visualization (ONT)

Oxford Nanopore (ONT) BAM files from dorado/guppy contain base modification tags (MM/ML) for 5mCG and 5hmCG. IGV can color reads by these modifications.

**Step 1**: Create an IGV config file for methylation:
```bash
echo "colorBy BASE_MODIFICATION" > methylation_prefs.txt
```

**Step 2**: Run igver with the config:
```bash
singularity exec \
  -B /data1 \
  docker://sahuno/igver:latest \
  igver \
    -i sample_modBaseCalls_dedup_sorted.bam \
    -r regions.bed \
    -o ./methylation_screenshots \
    -g hg38 \
    --dpi 600 \
    -d expand \
    -p 1000 \
    --no-singularity \
    -c methylation_prefs.txt
```

**Color interpretation**:
- **Red** = methylated CpG (5mC)
- **Blue** = unmethylated CpG
- Color intensity reflects the modification probability (from the ML tag)

**Requirements**: The BAM must contain `MM` and `ML` tags produced by a methylation-aware basecaller (dorado, guppy, etc.).

### Working with Haplotagged Reads
```bash
# Create IGV preferences for haplotype visualization
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
```

### Batch Processing Multiple Samples
```python
import igver
import glob

# Process all BAM files in a directory
bam_files = glob.glob("samples/*.bam")
regions = ["chr1:1000000-2000000", "chr2:3000000-4000000"]

for bam in bam_files:
    sample_name = os.path.basename(bam).replace('.bam', '')
    figures = igver.load_screenshots(
        paths=[bam],
        regions=regions,
        output_dir=f'screenshots/{sample_name}'
    )
```

## Supported Genomes

IGVer supports genome aliases that are automatically resolved. For example, passing `-g GRCh38` is equivalent to `-g hg38`.

| Organism | Aliases | IGV Genome |
|----------|---------|------------|
| Human | hg19, hg37, b37, GRCh37 | hg19 |
| Human | hg38, GRCh38 | hg38 |
| Human | hs1 | hs1 |
| Mouse | mm10, GRCm38 | mm10 |
| Mouse | mm39, GRCm39 | mm39 |
| Rat | rn6, Rnor_6.0 | rn6 |
| Dog | canFam3, CanFam3.1 | canFam3 |
| Zebrafish | danRer10, GRCz10 | danRer10 |
| Zebrafish | danRer11, GRCz11 | danRer11 |
| Fly | dm6, BDGP6 | dm6 |
| Worm | ce11, WBcel235 | ce11 |
| Yeast | sacCer3, R64 | sacCer3 |
| Arabidopsis | tair10, TAIR10 | tair10 |

See `igver/data/genome_map.yaml` for the full list.

## Lessons Learned & Common Pitfalls

### 1. Chromosome Naming Mismatch (`chr` prefix)

This is the most common issue. BAM files aligned to Broad's `Homo_sapiens_assembly38.fasta` (GRCh38) use `chr1`, `chr2`, etc. However, many tools (e.g. L1EM, some BED generators) output regions without the `chr` prefix (`1`, `2`, etc.). IGV's `hg38` genome expects `chr`-prefixed names.

**Symptom**: Empty screenshots or "region not found" errors.

**Fix**: Add `chr` prefix to BED files before passing to igver:
```bash
awk 'BEGIN{OFS="\t"} { if ($1 !~ /^chr/) $1 = "chr" $1; print }' regions.bed > regions_chrPrefix.bed
```

**Prevention**: Always verify that your BAM header (`samtools view -H file.bam | grep @SQ | head`) and region file use the same chromosome naming convention.

### 2. Nested Container Execution

When running igver inside a Singularity container, you **must** pass `--no-singularity`. Otherwise igver will attempt to launch a second Singularity container inside the first one, which will fail.

```bash
# Correct
singularity exec docker://sahuno/igver:latest igver ... --no-singularity

# Wrong - will fail with nested container error
singularity exec docker://sahuno/igver:latest igver ...
```

Docker containers are auto-detected and do not need this flag.

### 3. Bind-Mounting Data Directories

When using Singularity, all directories containing your input files (BAMs, BED files, IGV config) and the output directory must be bind-mounted:

```bash
singularity exec \
  --bind /data1/project,/data1/references,/home \
  docker://sahuno/igver:latest \
  igver ... --no-singularity
```

If a path is not mounted, igver will not be able to read your files inside the container.

### 4. Large Region Sets (>500 regions)

Generating screenshots for hundreds or thousands of regions (e.g., 1,483 L1 elements) can take a long time because each region requires IGV to navigate and render.

**Recommendations**:
- Run in a `screen` or `tmux` session, or submit as a SLURM job
- igver has a built-in retry mechanism (up to 2 iterations) for failed screenshots
- Consider splitting very large BED files and running in parallel

### 5. Display Mode for Long Reads (ONT/PacBio)

For long-read data, use `-d expand` and a large panel height (`-p 1000` or higher) to see individual reads clearly. The default `squish` mode compresses reads and may hide important details like methylation patterns.

```bash
igver -i ont_reads.bam -r regions.bed -d expand -p 1000 --dpi 600 -o ./screenshots
```

## Performance Tips

- **Pre-pull containers**: Download container images before running to avoid delays
- **Use absolute paths**: Provide absolute paths for files to avoid binding issues
- **Bind directories**: Use `-B` or `--bind` flags to mount data directories
- **Memory allocation**: Ensure sufficient memory for large genomic regions
- **Parallel processing**: Process multiple samples in parallel when possible

## Troubleshooting

### Container Issues
- **"singularity: command not found" error when using Singularity**: You must use the `--no-singularity` flag:
  ```bash
  singularity exec docker://sahuno/igver:latest igver ... --no-singularity
  ```
  This prevents IGVer from trying to run Singularity inside the container.

- **Permission denied**: Add bind flags for your data directories
  ```bash
  singularity exec -B /data,/home docker://sahuno/igver:latest igver ... --no-singularity
  ```

- **Image not found**: Pull the image first
  ```bash
  singularity pull docker://sahuno/igver:latest
  ```

### Common Errors
- **No screenshots generated**: 
  - Check if BAM files have indexes (.bai files)
  - Verify chromosome names match reference genome (chr1 vs 1)
  - Check output directory permissions

- **Region not found**:
  - Verify chromosome naming convention
  - Check if regions are within chromosome bounds
  - Ensure genome version matches your data

### IGV Display Issues
- **Screenshot width**: Modify IGV preferences file
  ```bash
  # In container: /opt/IGV_2.19.5/prefs.properties
  # Set: IGV.Bounds=0,0,800,480 for 800px width
  ```

## License

MIT License - see [LICENSE](LICENSE) file for details

## Authors

- Seongmin Choi ([@soymintc](https://github.com/soymintc)) - Original author
- Contributors welcome!

## Citation

If you use IGVer in your research, please cite:
```
Choi, S. (2024). IGVer: Automated IGV Screenshot Generation for Genomics. 
GitHub: https://github.com/shahcompbio/igver
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.