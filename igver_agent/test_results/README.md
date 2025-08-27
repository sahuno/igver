# Test Results Directory

This directory contains all test outputs from the IGVer Agent test suite.

## Directory Structure

```
test_results/
├── logic_test/           # Logic tests without Singularity
├── openai_test/          # OpenAI API integration tests
├── anthropic_test/       # Anthropic API integration tests
├── tagged_regions_test/  # Tests with tagged region files
├── batch_test/           # Batch processing tests
├── example_run/          # Example script outputs
└── reports/              # Test summary reports
```

## Running Tests

### Quick Test
```bash
# Run all tests
python run_tests.py

# Run specific test
python run_tests.py --test openai

# Show test summary
python run_tests.py --summary
```

### Individual Test Scripts
```bash
# Test logic without Singularity
python test_agent_logic_only.py

# Test with tagged regions
python test_agent_with_tagged_regions.py

# Test OpenAI integration
python test_agent_openai_quick.py
```

## Test Configuration

Test configuration is managed in `test_config.py`:
- Test output directories
- Test data locations
- Default test regions
- Singularity image paths

## Viewing Results

### Screenshots
Generated IGV screenshots are saved as PNG files:
```
test_results/*/genomic_ai_agent/*/chr*-*-*.png
```

### Reports
- **JSON Reports**: `analysis_results.json` - Complete analysis data
- **HTML Reports**: `report.html` - Interactive visualization
- **Test Reports**: `reports/test_report_*.json` - Test run summaries

### Example Output Structure
```
openai_test/
└── genomic_ai_agent/
    └── openai_test/
        ├── chr8-32534767-32536767.test.png    # Screenshot
        ├── chr19-11137898-11139898.test.png   # Screenshot
        ├── regions_list.txt                    # Input regions
        ├── analysis_results.json               # Analysis data
        └── report.html                         # HTML report
```

## Cleanup

To remove old test results:
```bash
# Keep only latest 3 test runs
python run_tests.py --cleanup

# Or use test_config directly
python -c "from test_config import cleanup_old_results; cleanup_old_results(3)"
```

## Disk Usage

Check disk usage:
```bash
du -sh test_results/
```

Typical usage:
- Per test run: ~1-5 MB
- With screenshots: ~100-500 KB per region
- AI analyses: ~1-2 MB per session

## Notes

- Test results are excluded from version control (see `.gitignore`)
- Screenshots are kept by default (set `remove_png=True` to delete)
- Failed tests leave partial results for debugging
- Use mock AI provider for testing without API keys