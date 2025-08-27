# IGVer Agent API Reference

## Classes

### `GenomicAIAgent`

Main agent class for genomic analysis workflows.

#### Constructor

```python
GenomicAIAgent(
    singularity_image: str = None,
    output_base_dir: str = None,
    config: Optional[AnalysisConfig] = None,
    ai_provider: str = "openai",
    ai_api_key: Optional[str] = None
)
```

**Parameters:**
- `singularity_image` (str, optional): Path to Singularity image or Docker URI. Defaults to `$IGVER_IMAGE` or `docker://sahuno/igver:latest`
- `output_base_dir` (str, optional): Base directory for output files. Defaults to `$TMPDIR/genomic_ai_agent`
- `config` (AnalysisConfig, optional): Configuration object with analysis parameters
- `ai_provider` (str): AI provider to use - "openai", "anthropic", or "mock"
- `ai_api_key` (str, optional): API key for AI provider. Defaults to environment variable

#### Methods

##### `comprehensive_analysis()`

Run complete genomic analysis workflow.

```python
comprehensive_analysis(
    bam_files: List[str],
    regions: List[str],
    session_name: Optional[str] = None,
    region_tags: Optional[List[str]] = None,
    context: str = "",
    ai_analysis: bool = True,
    save_report: bool = True
) -> Dict
```

**Parameters:**
- `bam_files` (List[str]): List of BAM file paths or text file containing BAM paths
- `regions` (List[str]): List of genomic regions in format "chr:start-end"
- `session_name` (str, optional): Name for analysis session. Auto-generated if not provided
- `region_tags` (List[str], optional): Tags for each region (used in filenames)
- `context` (str): Context for AI analysis (e.g., "BRCA screening")
- `ai_analysis` (bool): Enable AI interpretation of screenshots
- `save_report` (bool): Save JSON and HTML reports

**Returns:**
- Dict containing:
  - `session_name`: Name of the analysis session
  - `timestamp`: ISO format timestamp
  - `screenshots`: Dict mapping regions to screenshot paths
  - `ai_analyses`: Dict mapping regions to AI analysis results
  - `summary`: Summary statistics
  - `report_path`: Path to JSON report (if saved)
  - `html_report`: Path to HTML report (if saved)

**Example:**
```python
results = agent.comprehensive_analysis(
    bam_files=["tumor.bam", "normal.bam"],
    regions=["chr17:43044295-43045802"],
    region_tags=["BRCA1"],
    context="Hereditary cancer screening",
    ai_analysis=True
)
```

##### `generate_screenshots()`

Generate IGV screenshots without AI analysis.

```python
generate_screenshots(
    bam_files: List[str],
    regions: List[str],
    session_name: str = "analysis",
    region_tags: Optional[List[str]] = None,
    additional_mount_paths: Optional[List[str]] = None
) -> Dict[str, str]
```

**Returns:**
- Dict mapping region strings to screenshot file paths

##### `analyze_with_ai()`

Run AI analysis on existing screenshots.

```python
analyze_with_ai(
    screenshots: Dict[str, str],
    context: str = ""
) -> Dict[str, Dict]
```

**Parameters:**
- `screenshots`: Dict mapping regions to screenshot paths
- `context`: Context for analysis

**Returns:**
- Dict mapping regions to analysis results

---

### `AnalysisConfig`

Configuration dataclass for analysis parameters.

```python
@dataclass
class AnalysisConfig:
    genome: str = "hg38"
    output_format: str = "png"
    max_panel_height: int = 200
    overlap_display: str = "squish"
    igv_config: Optional[str] = None
    remove_png: bool = False
    dpi: int = 300
```

**Fields:**
- `genome`: Reference genome (hg19, hg38, mm10, mm39)
- `output_format`: Output format (png, svg, pdf)
- `max_panel_height`: Maximum panel height in pixels
- `overlap_display`: Read display mode (expand, squish, collapse)
- `igv_config`: Path to custom IGV preferences file
- `remove_png`: Remove screenshots after analysis
- `dpi`: Image resolution

---

### `GenomicRegion`

Dataclass representing a genomic region.

```python
@dataclass
class GenomicRegion:
    chromosome: str
    start: int
    end: int
    tag: Optional[str] = None
    name: Optional[str] = None
```

**Methods:**
- `__str__()`: Returns "chr:start-end" format
- `to_filename_base()`: Returns filename-safe string

---

### `AIGenomicInterpreter`

AI-powered screenshot interpreter.

```python
AIGenomicInterpreter(
    provider: str = "openai",
    api_key: Optional[str] = None
)
```

#### Methods

##### `analyze_screenshot()`

Analyze a single screenshot.

```python
analyze_screenshot(
    image_path: str,
    region: str,
    context: str = ""
) -> Dict
```

**Returns:**
- Dict containing:
  - `provider`: AI provider used
  - `model`: Model name
  - `region`: Genomic region
  - `analysis`: Detailed analysis text
  - `confidence`: Confidence score (0-1)
  - `timestamp`: ISO format timestamp
  - `error`: Error message (if failed)

---

### `InputValidator`

Static methods for input validation.

#### Methods

##### `validate_bam_files()`

Validate BAM files and check for indices.

```python
@staticmethod
validate_bam_files(bam_files: List[str]) -> List[str]
```

**Returns:**
- List of validated, absolute BAM file paths

**Raises:**
- `FileNotFoundError`: If BAM file doesn't exist

##### `parse_input_file()`

Parse a text file containing file paths.

```python
@staticmethod
parse_input_file(file_path: str) -> List[str]
```

**Returns:**
- List of validated file paths

##### `check_singularity()`

Check if Singularity is installed.

```python
@staticmethod
check_singularity() -> bool
```

---

### `SmartSingularityMounter`

Intelligent Singularity mount point management.

```python
SmartSingularityMounter(singularity_image: str)
```

#### Methods

##### `get_mount_args()`

Generate optimal mount arguments.

```python
get_mount_args(
    bam_files: List[str],
    output_dir: str,
    additional_paths: Optional[List[str]] = None
) -> str
```

**Returns:**
- String of mount arguments for Singularity (e.g., "-B /home -B /tmp")

---

## Helper Functions

### File I/O Functions

#### `_save_results()`

Save analysis results to JSON.

```python
_save_results(results: Dict, session_name: str) -> str
```

**Returns:**
- Path to saved JSON file

#### `_generate_html_report()`

Generate HTML report with screenshots.

```python
_generate_html_report(results: Dict, session_name: str) -> str
```

**Returns:**
- Path to generated HTML file

### Region Parsing Functions

#### `_parse_region()`

Parse genomic region string.

```python
_parse_region(region_str: str, tag: Optional[str] = None) -> GenomicRegion
```

**Parameters:**
- `region_str`: Region in "chr:start-end" format
- `tag`: Optional tag for the region

**Returns:**
- GenomicRegion object

---

## Exception Handling

The agent uses comprehensive exception handling:

```python
try:
    results = agent.comprehensive_analysis(...)
except FileNotFoundError as e:
    # Handle missing files
    print(f"File not found: {e}")
except RuntimeError as e:
    # Handle Singularity/IGV errors
    print(f"Runtime error: {e}")
except Exception as e:
    # Handle unexpected errors
    print(f"Unexpected error: {e}")
```

---

## Environment Variables

The agent respects these environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | None |
| `ANTHROPIC_API_KEY` | Anthropic API key | None |
| `IGVER_IMAGE` | Singularity/Docker image | docker://sahuno/igver:latest |
| `IGVER_NO_SINGULARITY` | Skip Singularity (for testing) | False |
| `TMPDIR` | Temporary directory | /tmp |

---

## Return Value Schemas

### Comprehensive Analysis Result

```python
{
    "session_name": str,
    "timestamp": str,  # ISO format
    "configuration": {
        "genome": str,
        "output_format": str,
        "ai_provider": str,
        "singularity_image": str
    },
    "input_summary": {
        "bam_files": List[str],
        "num_bam_files": int,
        "regions": List[str],
        "num_regions": int,
        "has_tags": bool,
        "context": str
    },
    "screenshots": Dict[str, str],  # region -> path
    "ai_analyses": Dict[str, Dict],  # region -> analysis
    "summary": {
        "total_regions": int,
        "screenshots_generated": int,
        "success_rate": str,  # percentage
        "ai_analyses_completed": int,
        "overall_status": str  # "Success" or "Failed"
    },
    "report_path": str,  # optional
    "html_report": str   # optional
}
```

### AI Analysis Result

```python
{
    "provider": str,  # "openai", "anthropic", or "mock"
    "model": str,     # "gpt-4o", "claude-3-opus", etc.
    "region": str,    # "chr1:1000-2000"
    "analysis": str,  # Detailed analysis text
    "confidence": float,  # 0.0 to 1.0
    "timestamp": str,     # ISO format
    "error": str      # Optional, only if failed
}
```

---

## Error Codes and Messages

| Error | Message | Solution |
|-------|---------|----------|
| `FileNotFoundError` | "BAM file not found: {path}" | Check file path exists |
| `RuntimeError` | "Singularity is not installed" | Install Singularity |
| `ValueError` | "Invalid region format: {region}" | Use chr:start-end format |
| `APIError` | "OpenAI API error: {message}" | Check API key and quota |

---

## Performance Considerations

### Memory Usage
- Each screenshot: ~100-500 KB
- AI analysis per region: ~1-2 MB
- Typical session (10 regions): ~10-20 MB total

### API Rate Limits
- OpenAI: 500 requests/minute (GPT-4o)
- Anthropic: 1000 requests/minute (Claude-3)

### Optimization Tips
1. Process regions in batches of 10-20
2. Use `remove_png=True` to save disk space
3. Cache AI analyses for repeated regions
4. Use mock provider for testing

---

## Thread Safety

The agent is NOT thread-safe. For parallel processing:

```python
from multiprocessing import Pool

def process_batch(args):
    bam_files, regions = args
    agent = GenomicAIAgent(...)
    return agent.comprehensive_analysis(bam_files, regions)

with Pool(processes=4) as pool:
    results = pool.map(process_batch, batches)
```