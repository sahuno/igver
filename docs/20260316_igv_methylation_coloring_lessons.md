# IGV Methylation Coloring with igver: Lessons Learned

**Date**: 2026-03-16
**Author**: Samuel Ahuno
**Project**: GIAB ONT — HG002/HG006 methylation visualization
**Container**: `igver_latest.sif` (downloaded 2026-03-16, IGV 2.19.5 bundled)

---

## Summary

Getting base modification (5mC) coloring to render in headless IGV screenshots
via igver required solving two independent bugs. This document records the
debugging timeline, root causes, and the final working configuration for future
reference.

---

## Problem Statement

IGV screenshots at LTR loci (and MTHFR promoter) showed **uniform gray reads**
with no red/blue methylation marks, despite the input BAMs/CRAMs containing
valid MM/ML base modification tags (confirmed via `samtools view`).

---

## Root Cause 1: igver `-c` flag was broken

The igver tool accepts a `-c <config_file>` flag meant to inject per-track
commands (like `colorBy`) into the generated batch script. The old igver version
had a bug where it injected the config file contents as **raw text** without
converting `KEY=VALUE` format to valid IGV batch syntax.

**Fix**: igver commit `605c9e38` (deployed in `igver_latest.sif` downloaded
2026-03-16) now warns if `-c` file uses `KEY=VALUE` format and passes lines
through correctly as batch commands.

## Root Cause 2: Invalid `colorBy` value

The config file used:

```
colorBy BASE_MODIFICATION_5MC    # WRONG
```

`BASE_MODIFICATION_5MC` is **not** a valid `colorBy` batch command value. The
valid values (from IGV 2.19.X source, `AlignmentTrack.ColorOption` enum) are:

| Batch command value        | What it does                                    |
|----------------------------|-------------------------------------------------|
| `BASE_MODIFICATION`        | Colors reads by all base modifications (5mC, 6mA, etc.) |
| `BASE_MODIFICATION_2COLOR` | Two-color mode (red = methylated, blue = unmethylated) |

The `_5MC` suffix is only valid as a **preference** value:

```
preference SAM.COLOR_BY BASE_MODIFICATION_5MC   # valid for preference command
preference SAM.COLOR_BY BASE_MODIFICATION        # also valid for preference command
colorBy BASE_MODIFICATION                        # valid for colorBy batch command
colorBy BASE_MODIFICATION_5MC                    # INVALID — silently ignored by IGV
```

**Fix**: Changed `igv_prefs_methyl.properties` to:

```
colorBy BASE_MODIFICATION
```

---

## Debugging Timeline

### Attempt 1: Scripts 06-08 (all samples, LTR loci + coding genes + promoters)

- Used old igver container + `colorBy BASE_MODIFICATION_5MC` in config
- Both bugs active: `-c` flag broken AND wrong colorBy value
- **Result**: All screenshots gray

### Attempt 2: Script 09 — manual batch with `preference` + `colorBy`

- Bypassed igver, wrote IGV batch script directly
- Used `preference SAM.COLOR_BY BASE_MODIFICATION_5MC` (set before load)
- Also tried `colorBy BASE_MODIFICATION_5MC` (set after load)
- Ran via `xvfb-run igv.sh -b`
- **Result**: `test_pref_before_load.png` generated (32K) — gray reads
- The `colorBy` command was silently ignored because `BASE_MODIFICATION_5MC`
  is not a valid batch command value
- The `preference` was set before load, which should work, but used
  `BASE_MODIFICATION_5MC` which may have been interpreted differently by the
  preference system vs the batch system

### Attempt 3: Script 10 — persistent `prefs.properties` file

- Wrote `SAM.COLOR_BY=BASE_MODIFICATION_5MC` to `~/igv/prefs.properties`
- Used a simple batch script with no colorBy/preference commands
- **Result**: `test_prefsfile_methyl.png` (32K) — gray reads
- The persistent preference was correctly written but `BASE_MODIFICATION_5MC`
  as a preference file value did not trigger coloring in headless mode

### Attempt 4: Script 11 — zoom level tests

- Set both `preference SAM.COLOR_BY BASE_MODIFICATION_5MC` in batch AND
  `~/igv/prefs.properties`
- Tested 3 zoom levels: 100bp, 250bp, 1000bp
- **Result**: All 3 PNGs generated — all gray
- Ruled out zoom level as the issue

### Attempt 5: Script 12 — CRAM to BAM conversion + direct batch

- Converted CRAM to BAM (chr1 only) to rule out CRAM-specific issues
- Verified MM/ML tags present in BAM with `samtools view`
- Step 4: BAM with no coloring (control) — gray (expected)
- Step 5: Manual batch with `preference SAM.COLOR_BY BASE_MODIFICATION_5MC`
  set before load — gray
- Step 6: igver with `-c igv_prefs_methyl.properties` (still `BASE_MODIFICATION_5MC`) — gray
- Step 7: CRAM with same batch approach — gray
- **Key insight**: Even with a confirmed-good BAM, methylation coloring
  did not render. This isolated the issue to the colorBy value, not the
  input format.

### Attempt 6: Script 13 — final retest with BOTH bugs fixed

Updated `igver_latest.sif` (igver `-c` fix) + corrected config to
`colorBy BASE_MODIFICATION`.

| Test | Input | Config approach                              | Result     |
|------|-------|----------------------------------------------|------------|
| A    | BAM   | `colorBy BASE_MODIFICATION` via igver `-c`   | **Colored** (80K) |
| B    | BAM   | `preference SAM.COLOR_BY BASE_MODIFICATION` via igver `-c` | **Colored** (80K) |
| C    | CRAM  | `colorBy BASE_MODIFICATION` via igver `-c`   | **Colored** (79K) |
| D    | BAM   | No config (control)                          | Gray (35K) |

**All colored tests produced ~80K PNGs vs 35K for the gray control** — the
file size difference alone is a reliable indicator of whether coloring worked.

---

## Working Configuration

### Config file: `igv_prefs_methyl.properties`

```
colorBy BASE_MODIFICATION
```

### igver command (production)

```bash
singularity exec --bind /data1/greenbab \
    /data1/greenbab/software/images/igver_latest.sif igver \
    --input <BAM_or_CRAM> <optional_tracks> \
    -r <region_or_regions_file> \
    -o <output_dir> \
    --dpi 600 -d expand -p 1000 -f png \
    --genome <reference.fna> \
    --no-singularity \
    -c igv_prefs_methyl.properties
```

### Key flags

| Flag | Purpose |
|------|---------|
| `--no-singularity` | Required when already inside a singularity container |
| `-c <file>` | Config file with batch commands injected per track |
| `-d expand` | Expand reads to show individual alignments |
| `-p 1000` | Max panel height in pixels |
| `--genome <ref>` | Reference FASTA (required for CRAM decoding) |

---

## Key Takeaways

### 1. BAM and CRAM produce identical methylation screenshots

No need to convert CRAMs to BAMs. As long as the reference FASTA is provided
via `--genome`, igver/IGV reads MM/ML tags from CRAMs just fine.

### 2. `colorBy` vs `preference SAM.COLOR_BY` — both work, but values differ

- **`colorBy` batch command**: Use `BASE_MODIFICATION` or `BASE_MODIFICATION_2COLOR`.
  Do NOT use `BASE_MODIFICATION_5MC` — it is silently ignored.
- **`preference SAM.COLOR_BY`**: Use `BASE_MODIFICATION` (works). `BASE_MODIFICATION_5MC`
  may work in interactive IGV but did not reliably work in headless mode during
  our tests.
- **Recommendation**: Use `colorBy BASE_MODIFICATION` in igver config files. It is
  the simplest and most reliable approach.

### 3. File size is a quick diagnostic

Methylation-colored screenshots are roughly **2x the file size** of gray
screenshots at the same locus (~80K vs ~35K for 1kb window at 600 DPI). This
is a fast way to check if coloring worked without opening every image.

### 4. Always `unset SINGULARITY_BIND APPTAINER_BIND` before igver

Stale bind variables from the login node environment can cause mount failures
inside the container. Add this to the top of every script:

```bash
unset SINGULARITY_BIND APPTAINER_BIND 2>/dev/null || true
```

### 5. IGV batch command errors are silent

IGV does not error or warn when a `colorBy` value is invalid — it simply
falls back to default coloring. This makes debugging extremely difficult.
Always verify against the `AlignmentTrack.ColorOption` enum values in the
IGV source code.

---

## Data and Paths

### Samples

| Sample | Flowcell   | CRAM path |
|--------|------------|-----------|
| HG002  | PAW71238   | `analysis/wf-human-variation/sup/HG002/PAW71238/output/HG002_PAW71238.haplotagged.cram` |
| HG002  | PAW70337   | `analysis/wf-human-variation/sup/HG002/PAW70337/output/HG002_PAW70337.haplotagged.cram` |
| HG006  | PAY77227   | `analysis/wf-human-variation/sup/HG006/PAY77227/output/HG006_PAY77227.haplotagged.cram` |
| HG006  | PBA16846   | `analysis/wf-human-variation/sup/HG006/PBA16846/output/HG006_PBA16846.haplotagged.cram` |

All paths relative to `/data1/greenbab/projects/GIAB_ont/GIAB_data/giab_2025.01/`.

**Note**: CRAMs were renamed from `SAMPLE.haplotagged.cram` to `{patient}_{flowcell}.haplotagged.cram`
on 2026-03-16 so that IGV track labels are distinguishable in multi-sample views.

### Test BAM (chr1 subset)

```
results/igv_test_bam_methyl/HG006_PAY77227.chr1.haplotagged.bam   (7.1G)
```

Created from HG006/PAY77227 CRAM via:

```bash
samtools view -@ 4 -b -T $REF -o $BAM $CRAM chr1
samtools index -@ 4 $BAM
```

### Reference genome

```
/data1/greenbab/projects/GIAB_ont/GIAB_data/ref/GCA_000001405.15_GRCh38_no_alt_analysis_set.fna
```

### LTR target loci

| Locus | Coordinates | Label |
|-------|-------------|-------|
| LTR14C | chr16:19401566-19402152 | SU2C-371 |
| LTR10F | chr4:160826459-160826767 | SU2C-118 |
| LTR16A2 | chr16:71344432-71344622 | SU2C-118 |

### Test locus (MTHFR promoter)

```
chr1:11805464-11806464
```

Used for all debugging iterations because the chr1-only BAM covers it.

### Container

```
/data1/greenbab/software/images/igver_latest.sif
```

Downloaded 2026-03-16 17:24. Contains igver with `-c` fix + IGV 2.19.5.

### Scripts (in order of creation)

| Script | Purpose | Outcome |
|--------|---------|---------|
| `06_igv_screenshots_all_methyl.sh` | First attempt — all samples at LTR loci | Gray (both bugs) |
| `07_igv_screenshots_coding_genes_methyl.sh` | Coding gene loci | Gray |
| `08_igv_screenshots_promoters_methyl.sh` | Promoter loci | Gray |
| `09_igv_test_methyl_colorby.sh` | Manual batch with colorBy + preference | Gray (wrong value) |
| `10_igv_test_methyl_prefsfile.sh` | Persistent prefs.properties approach | Gray (wrong value) |
| `11_igv_test_methyl_zoom.sh` | Zoom level test (100bp/250bp/1000bp) | Gray (wrong value) |
| `12_cram_to_bam_igv_methyl_test.sh` | CRAM-to-BAM + multiple approaches | Gray (wrong value) |
| `13_igver_methyl_retest.sh` | Final retest with both fixes | **Colored** |
| `14_igv_screenshots_LTR_methyl_final.sh` | Production run — all samples x LTR loci | Pending |

### Results directories

| Directory | Contents |
|-----------|----------|
| `results/igv_methyl_retest/` | Test A-D comparison PNGs (the definitive test) |
| `results/igv_test_bam_methyl/` | BAM + early batch test outputs |
| `results/igv_test_colorby/` | Script 09 outputs |
| `results/igv_test_prefsfile/` | Script 10 outputs |
| `results/igv_test_methyl_zoom/` | Script 11 outputs |
| `results/igv_LTR_methyl_final/` | Script 14 outputs (production) |
