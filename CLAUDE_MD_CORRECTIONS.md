# CLAUDE.md Corrections Needed

This document lists contradictions found between CLAUDE.md documentation and the actual igver implementation.

Generated: 2025-08-27

## 1. CLI Flag Corrections

### Singularity Image Flag
**Location:** Line 38

**Current (INCORRECT):**
```bash
igver -i input.bam -r "chr1:1000-2000" -g hg38 -sif /path/to/igver.sif
```

**Should be (CORRECT):**
```bash
igver -i input.bam -r "chr1:1000-2000" -g hg38 --singularity-image /path/to/igver.sif
```

**Issue:** The `-sif` flag doesn't exist. The correct flag is `--singularity-image`.

---

## 2. Python API Parameter Names

### load_screenshots() Function
**Location:** Lines 63-68

**Current (INCORRECT):**
```python
figures = igver.load_screenshots(
    bam_paths=['sample1.bam', 'sample2.bam'],
    regions=['chr1:1000-2000', 'chr2:3000-4000'],
    outdir='screenshots/',
    genome='hg19'
)
```

**Should be (CORRECT):**
```python
figures = igver.load_screenshots(
    paths=['sample1.bam', 'sample2.bam'],        # Changed: bam_paths → paths
    regions=['chr1:1000-2000', 'chr2:3000-4000'],
    output_dir='screenshots/',                    # Changed: outdir → output_dir
    genome='hg19'
)
```

**Issues:**
- Parameter `bam_paths` should be `paths`
- Parameter `outdir` should be `output_dir`
- The `regions` parameter is required (already correct in doc)

### create_batch_script() Function
**Location:** Line 71

**Current (INCORRECT):**
```python
igver.create_batch_script(bam_paths, regions, genome, outdir)
```

**Should be (CORRECT):**
```python
# Correct function signature with proper parameter names and order
batch_file, png_paths = igver.create_batch_script(
    paths,           # Not bam_paths
    regions,         
    output_dir,      # Not outdir, and comes before genome
    genome='hg19'    # genome is 4th parameter with default
)
```

**Issues:**
- Parameter `bam_paths` should be `paths`
- Parameter `outdir` should be `output_dir`
- Parameter order: `paths, regions, output_dir, genome` (not `paths, regions, genome, output_dir`)
- Function returns a tuple: `(batch_file_path, list_of_png_paths)`

---

## 3. Non-existent Public Functions

### load_image() Function
**Location:** Line 88

**Current (INCORRECT):**
```
- `load_image()`: Loads generated screenshots
```

**Should be (REMOVED or CORRECTED):**
```
# This function doesn't exist in the public API
# There's an internal _load_image() function but it's not exposed
# This line should be removed from the documentation
```

**Issue:** The `load_image()` function is not part of the public API. Only `_load_image()` exists as an internal function.

---

## 4. Output File Naming Convention

### Screenshot Naming Pattern
**Location:** Line 134

**Current (PARTIALLY INCORRECT):**
```
3. **Output Naming**: Screenshots are named as `{bam_basename}_{region}.png`
```

**Should be (CORRECT):**
```
3. **Output Naming**: Screenshots are named as:
   - Without tags: `{region_formatted}.png` (e.g., `chr1-1000-2000.png`)
   - With tags: `{region_formatted}.{tag}.png` (e.g., `chr1-1000-2000.test.png`)
   - Region formatting: colons become hyphens (`:` → `-`)
   - Note: When multiple BAMs are loaded together, they appear in the same screenshot
```

**Issue:** The actual naming doesn't include the BAM basename when multiple BAMs are visualized together. The region is the primary identifier.

---

## 5. Additional Clarifications Needed

### Input Methods
**Location:** Lines 31-35 (CLI Usage section)

**Current:**
```bash
# Multiple BAM files and regions
igver -i sample1.bam sample2.bam -r regions.txt -o screenshots/
```

**Add clarification:**
```bash
# Multiple BAM files and regions (space-separated, NOT comma-separated)
igver -i sample1.bam sample2.bam -r regions.txt -o screenshots/

# INCORRECT - comma-separated doesn't work:
# igver -i sample1.bam,sample2.bam  # This treats it as single filename
```

---

## 6. Verified Correct Information

The following are **CORRECT** in the current documentation:

1. **.txt file support** (Lines 41-56) - Works correctly with latest repository version
2. **Comment handling** - Lines starting with `#` are properly ignored
3. **Empty line handling** - Empty lines are properly skipped
4. **Tilde expansion** - `~` is correctly expanded to home directory
5. **Container architecture** - Singularity usage is accurate
6. **Genome aliases** - Mapping like GRCh38 → hg38 works correctly

---

## Implementation Priority

1. **HIGH**: Fix Python API examples (breaks user code)
2. **HIGH**: Fix CLI flag documentation (causes command failures)  
3. **MEDIUM**: Correct output naming documentation (causes confusion)
4. **LOW**: Remove non-existent function references
5. **LOW**: Add clarifications about input formats

---

## Testing

After corrections are made, verify with:

```bash
# Test corrected CLI command
igver -i test/test_tumor.bam -r "chr1:1000-2000" -g hg38 --singularity-image downloaded_image/igver_latest.sif

# Test corrected Python API
python -c "
import igver
figures = igver.load_screenshots(
    paths=['test/test_tumor.bam'],
    regions=['chr1:1000-2000'],
    output_dir='/tmp/test',
    genome='hg19'
)
"
```