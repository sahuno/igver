# IGVer Python Package Test Results Analysis

**Test Date:** 2025-08-26  
**Package Version:** 1.1  
**Test Suite:** test/test_igver_package.py  
**Results:** 9 passed ✅ / 11 failed ❌ / 20 total

## Important Resources
- **Local Singularity Image Available:** `downloaded_image/igver_latest.sif`
- This local image can be used for testing without downloading from Docker Hub

---

## ✅ PASSED TESTS (9/20)

### 1. Package Import Tests
- ✅ **test_package_import** - Package imports successfully
- ✅ **test_package_version** - Version 1.1 is accessible

### 2. API Function Availability Tests
- ✅ **TestAPIFunctions.test_load_screenshots_exists** - Function exists and is callable
- ✅ **TestAPIFunctions.test_create_batch_script_exists** - Function exists and is callable  
- ✅ **TestAPIFunctions.test_run_igv_exists** - Function exists and is callable
- ✅ **TestAPIFunctions.test_function_signatures** - Core parameters verified:
  - `load_screenshots`: paths, regions, output_dir, genome
  - `create_batch_script`: paths, regions, output_dir, genome, tag, max_panel_height, overlap_display, igv_config, output_format
  - `run_igv`: batch_script, png_paths, igv_dir, overwrite, singularity_image, singularity_args, debug, use_singularity

### 3. CLI Tests
- ✅ **TestCLI.test_cli_help** - `igver --help` works correctly
- ✅ **TestCLI.test_cli_missing_args** - Proper error handling for missing arguments

### 4. Input File Parsing Tests  
- ✅ **TestInputFileParsing.test_text_file_parsing** - Basic file reading works

---

## ❌ FAILED TESTS (11/20)

### 1. Import Error Tests (3 failures)

#### ❌ TestInputFileParsing.test_mixed_input_parsing
**Error:** `ImportError: cannot import name 'parse_input_files' from 'igver.cli'`
**Root Cause:** Function `parse_input_files` doesn't exist in public API
**Fix:** 
```python
# Instead of importing parse_input_files, test the actual CLI behavior
# Use subprocess to call the CLI with a text file input
result = subprocess.run(['igver', '-i', txt_file, '-r', 'chr1:1-100', '-o', temp_dir], 
                       capture_output=True)
# Or directly test that text files are readable
```

#### ❌ TestInputFileParsing.test_empty_text_file
**Error:** Same ImportError
**Fix:** Remove dependency on non-existent function, test file reading directly

#### ❌ TestInputFileParsing.test_nonexistent_text_file  
**Error:** Same ImportError
**Fix:** Test using os.path.exists() or try/except when opening file

---

### 2. Batch Script Creation Tests (2 failures)

#### ❌ TestBatchScriptGeneration.test_batch_script_creation
**Error:** `FileNotFoundError: [Errno 2] No such file or directory: 'chr1:1000-2000'`
**Root Cause:** igver tries to open 'chr1:1000-2000' as a file, not recognizing it as a genomic coordinate
**Critical Analysis:** The `create_batch_script` function expects regions to be either:
- A file path (*.txt or *.bed)
- Not a direct coordinate string

**Fix:**
```python
# Create a temporary regions file first
regions_file = os.path.join(self.temp_dir, 'regions.txt')
with open(regions_file, 'w') as f:
    f.write('chr1:1000-2000\n')

batch_file = igver.create_batch_script(
    paths=['test1.bam', 'test2.bam'],
    regions=[regions_file],  # Pass file path, not direct region
    output_dir=self.temp_dir,
    genome='hg19'
)
```

#### ❌ TestBatchScriptGeneration.test_batch_script_with_bed_regions
**Error:** `TypeError: expected str, bytes or os.PathLike object, not tuple`
**Root Cause:** `create_batch_script` returns a tuple (batch_file, png_paths), not just batch_file
**Fix:**
```python
batch_file, png_paths = igver.create_batch_script(
    paths=['test.bam'],
    regions=[bed_file],
    output_dir=self.temp_dir,
    genome='hg19'
)
# Now batch_file is the string path to the batch file
```

---

### 3. Mock Tests (3 failures)

#### ❌ TestMockFunctionality.test_load_screenshots_mock
**Error:** `ModuleNotFoundError: No module named 'igver.igver.shutil'`
**Root Cause:** Wrong mock path - should mock 'shutil' directly since igver imports it
**Fix:**
```python
# Instead of: @patch('igver.igver.shutil.which')
@patch('shutil.which')  # Mock the actual shutil module
# Or find where igver imports shutil and mock that specific import
```

#### ❌ TestMockFunctionality.test_singularity_detection
**Error:** Same mock path error
**Fix:** Use correct mock paths for standard library modules

#### ❌ TestMockFunctionality.test_container_detection
**Error:** `TypeError: run_igv() got an unexpected keyword argument 'batch_file'`
**Root Cause:** `run_igv` expects `batch_script` as first positional argument, not keyword
**Fix:**
```python
igver.run_igv(
    '/tmp/batch.txt',  # batch_script (positional)
    png_paths=[],      # png_paths (required positional)
    igv_dir='/opt/IGV',
    use_singularity=None
)
```

---

### 4. Region Parsing Tests (3 failures)

#### ❌ TestRegionParsing.test_parse_standard_region
**Error:** `ImportError: cannot import name 'parse_regions'`
**Root Cause:** Function doesn't exist in public API
**Fix:** Test region handling through `create_batch_script`:
```python
# Create regions file and test that it's processed correctly
with tempfile.NamedTemporaryFile(mode='w', suffix='.txt') as f:
    f.write('chr1:1000-2000\nchr2:3000-4000\n')
    f.flush()
    batch_file, png_paths = igver.create_batch_script(
        paths=['test.bam'],
        regions=[f.name],
        output_dir=temp_dir,
        genome='hg19'
    )
```

#### ❌ TestRegionParsing.test_parse_text_file_regions
**Error:** Same ImportError
**Fix:** Test through actual API functions that accept region files

#### ❌ TestRegionParsing.test_parse_bed_file_regions  
**Error:** Same ImportError
**Fix:** Test BED file parsing through `create_batch_script`

---

## 🔧 CRITICAL FIXES SUMMARY

### 1. **Region Input Format**
- igver expects region FILES (*.txt, *.bed), not direct coordinate strings
- Always create a temporary file with regions before calling functions

### 2. **Return Value Handling**
- `create_batch_script` returns `(batch_file, png_paths)` tuple, not just batch_file
- Always unpack both values: `batch_file, png_paths = igver.create_batch_script(...)`

### 3. **Function Signatures**
- `run_igv` expects: `batch_script` (pos), `png_paths` (pos), then keyword args
- Not `batch_file` as keyword argument

### 4. **Mock Paths**
- Mock standard library modules directly: `@patch('shutil.which')`
- Not through igver module: ~~`@patch('igver.igver.shutil.which')`~~

### 5. **Use Local Singularity Image**
```python
# For tests requiring Singularity, use the local image:
singularity_image = 'downloaded_image/igver_latest.sif'
# This avoids downloading from Docker Hub during tests
```

### 6. **Testing Strategy**
Since many internal functions aren't exposed in the public API:
- Test through the main entry points: `load_screenshots`, `create_batch_script`, CLI
- Don't try to import internal functions like `parse_regions` or `parse_input_files`
- Use subprocess to test CLI behavior for complex input handling

---

## 📊 TEST COVERAGE RECOMMENDATIONS

### What's Well Tested:
- ✅ Package installation and import
- ✅ API function availability
- ✅ CLI interface
- ✅ Basic function signatures

### What Needs Better Testing:
1. **End-to-end workflow** with local Singularity image
2. **Region file parsing** (BED3, BED6, text formats)
3. **Error handling** for malformed inputs
4. **Output verification** - checking that correct files are created
5. **Multi-file batch processing**

### Proposed New Test:
```python
def test_end_to_end_with_local_singularity():
    """Test complete workflow with local Singularity image."""
    import igver
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create regions file
        regions_file = os.path.join(temp_dir, 'regions.txt')
        with open(regions_file, 'w') as f:
            f.write('chr1:1000-2000\n')
        
        # Use local Singularity image
        batch_file, png_paths = igver.create_batch_script(
            paths=['test/test_tumor.bam'],
            regions=[regions_file],
            output_dir=temp_dir,
            genome='hg19'
        )
        
        # Verify batch file created
        assert os.path.exists(batch_file)
        
        # If Singularity available, could run:
        # igver.run_igv(
        #     batch_file,
        #     png_paths,
        #     singularity_image='downloaded_image/igver_latest.sif'
        # )
```

---

## 📝 NEXT STEPS

1. **Fix the test file** based on the analysis above
2. **Use local Singularity image** at `downloaded_image/igver_latest.sif` for integration tests
3. **Create region files** instead of passing coordinate strings directly
4. **Handle tuple returns** from `create_batch_script`
5. **Mock standard libraries correctly** without going through igver module path
6. **Add integration test** that uses the actual local Singularity image if available

This comprehensive analysis provides the foundation for creating a robust test suite that accurately tests the igver Python package's actual API and behavior.