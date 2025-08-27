# 🧬 IGVer Genomic AI Agent

An intelligent agent that automates IGV (Integrative Genomics Viewer) screenshot generation and provides AI-powered genomic interpretation using GPT-4 or Claude vision models.

## 🌟 Features

- **Automated IGV Screenshots**: Generate high-quality IGV visualizations for multiple BAM files across multiple genomic regions
- **AI-Powered Analysis**: Leverage OpenAI GPT-4o or Anthropic Claude for intelligent interpretation of genomic visualizations
- **Smart Input Handling**: Support for tagged regions, BED files, and batch processing
- **Comprehensive Reporting**: Generate HTML and JSON reports with screenshots and AI analyses
- **Production-Ready**: Robust error handling, logging, and validation

## 📋 Prerequisites

- Python 3.8+
- Singularity (for containerized IGV execution)
- IGVer package (parent directory)
- OpenAI API key (for GPT-4 analysis) or Anthropic API key (for Claude analysis)

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository (if not already done)
git clone <repository-url>
cd igver/igver_agent

# Run the automated setup script
./setup_agent.sh
```

The setup script will:
- Create a Python virtual environment
- Install all dependencies (IGVer, OpenAI, Anthropic, etc.)
- Create configuration templates
- Verify the installation

### 2. Configuration

Copy the environment template and add your API keys:

```bash
cp .env.template .env
nano .env  # or your preferred editor
```

Add your API key(s):
```bash
# OpenAI API Key (for GPT-4 vision analysis)
OPENAI_API_KEY=sk-your-api-key-here

# Anthropic API Key (for Claude vision analysis)  
ANTHROPIC_API_KEY=your-anthropic-key-here

# IGVer Settings
IGVER_IMAGE=docker://sahuno/igver:latest
TMPDIR=/tmp
```

### 3. Basic Usage

```bash
# Activate the virtual environment
source venv/bin/activate

# Run with the convenience script
./run_agent.sh

# Or use Python directly
python main_igver_agent_fixed.py
```

## 📖 Detailed Usage

### Python API

```python
from main_igver_agent_fixed import GenomicAIAgent, AnalysisConfig

# Configure analysis parameters
config = AnalysisConfig(
    genome="hg19",              # Reference genome
    output_format="png",        # Output format (png, svg, pdf)
    max_panel_height=200,       # IGV panel height
    overlap_display="squish",   # Read overlap display mode
    remove_png=False           # Keep generated screenshots
)

# Initialize the agent
agent = GenomicAIAgent(
    singularity_image="path/to/igver.sif",  # Or "docker://sahuno/igver:latest"
    output_base_dir="/path/to/output",
    config=config,
    ai_provider="openai",  # or "anthropic" or "mock" for testing
    ai_api_key="your-api-key"  # Optional if set in environment
)

# Run comprehensive analysis
results = agent.comprehensive_analysis(
    bam_files=["sample1.bam", "sample2.bam"],
    regions=["chr1:1000-2000", "chr2:3000-4000"],
    region_tags=["variant1", "variant2"],  # Optional tags for filenames
    session_name="my_analysis",
    context="Clinical variant validation for patient X",
    ai_analysis=True,  # Enable AI interpretation
    save_report=True   # Generate HTML and JSON reports
)

# Access results
print(f"Screenshots generated: {results['summary']['screenshots_generated']}")
print(f"Report saved to: {results.get('report_path')}")
```

### Command-Line Examples

#### Simple Analysis
```python
# Analyze specific regions in BAM files
agent.comprehensive_analysis(
    bam_files=["tumor.bam", "normal.bam"],
    regions=["chr17:43044295-43045802"],  # BRCA1
    context="BRCA1 mutation screening"
)
```

#### Using Region Files
```python
# Load regions from a file (one region per line)
with open("regions.txt") as f:
    regions = [line.strip() for line in f if line.strip()]

results = agent.comprehensive_analysis(
    bam_files=["sample.bam"],
    regions=regions,
    session_name="batch_analysis"
)
```

#### Tagged Regions
```python
# Tag regions for better organization
regions = [
    "chr17:43044295-43045802",  # BRCA1
    "chr13:32315086-32400266",  # BRCA2
    "chr9:21967752-21975098"    # CDKN2A
]

tags = [
    "BRCA1_exon11",
    "BRCA2_exon10", 
    "CDKN2A_deletion"
]

results = agent.comprehensive_analysis(
    bam_files=["sample.bam"],
    regions=regions,
    region_tags=tags  # Creates files like: chr17-43044295-43045802.BRCA1_exon11.png
)
```

## 📁 Input File Formats

### BAM List File (.txt)
```text
# List of BAM files for analysis
/path/to/sample1.bam
/path/to/sample2.bam
~/data/sample3.bam
```

### Tagged Regions File (.txt)
```text
# Format: region tag
chr8:32534767-32536767 amplification
chr19:11137898-11139898 deletion
chr1:156104930-156105100 mutation_hotspot
```

### BED File (.bed)
```text
# Standard BED3 or BED6 format
chr1	1000	2000	variant1	100	+
chr2	3000	4000	variant2	200	-
```

## 🔧 Configuration Options

### AnalysisConfig Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `genome` | str | "hg38" | Reference genome (hg19, hg38, mm10, mm39) |
| `output_format` | str | "png" | Output format (png, svg, pdf) |
| `max_panel_height` | int | 200 | Maximum IGV panel height in pixels |
| `overlap_display` | str | "squish" | Read display mode (expand, squish, collapse) |
| `igv_config` | str | None | Path to custom IGV preferences file |
| `remove_png` | bool | False | Remove screenshots after analysis |
| `dpi` | int | 300 | Image resolution (dots per inch) |

### AI Provider Options

| Provider | Model | Description | Requirements |
|----------|-------|-------------|--------------|
| `openai` | GPT-4o | Advanced vision model with genomics understanding | OpenAI API key |
| `anthropic` | Claude-3-Opus | High-quality analysis with detailed explanations | Anthropic API key |
| `mock` | N/A | Mock analysis for testing without API keys | None |

## 📊 Output Files

The agent generates several output files:

```
output_dir/
├── session_name/
│   ├── chr1-1000-2000.png          # IGV screenshot
│   ├── chr2-3000-4000.variant1.png # Tagged screenshot
│   ├── analysis_results.json       # Complete analysis data
│   ├── report.html                 # Interactive HTML report
│   ├── bam_list.txt               # Input BAM files (if multiple)
│   └── regions_list.txt           # Input regions (if multiple)
```

### JSON Report Structure
```json
{
  "session_name": "my_analysis",
  "timestamp": "2024-01-01T12:00:00",
  "configuration": {
    "genome": "hg19",
    "output_format": "png",
    "ai_provider": "openai"
  },
  "screenshots": {
    "chr1:1000-2000": "/path/to/screenshot.png"
  },
  "ai_analyses": {
    "chr1:1000-2000": {
      "provider": "openai",
      "model": "gpt-4o",
      "analysis": "Detailed genomic interpretation...",
      "confidence": 0.85
    }
  },
  "summary": {
    "total_regions": 10,
    "screenshots_generated": 10,
    "success_rate": "100%"
  }
}
```

## 🧪 Testing

### Test with Mock AI (No API Key Required)
```bash
python test_agent_logic_only.py
```

### Test with Real Data
```bash
python test_agent_with_tagged_regions.py
```

### Quick OpenAI Test
```bash
python test_agent_openai_quick.py
```

## 🤖 AI Analysis Features

The AI agent analyzes IGV screenshots for:

1. **Coverage Assessment**
   - Average depth and uniformity
   - Coverage gaps or drops
   - Potential duplications

2. **Read Alignment Quality**
   - Soft-clipped reads (structural variants)
   - Misaligned or improperly paired reads
   - Read orientation anomalies

3. **Variant Detection**
   - SNPs/SNVs with allele frequencies
   - Insertions and deletions
   - Structural variants (inversions, translocations, CNVs)

4. **Technical Quality Issues**
   - PCR duplicates
   - Mapping quality problems
   - Sequencing errors or biases

5. **Clinical Relevance**
   - Known pathogenic variant hotspots
   - Affected genes and clinical significance
   - Validation recommendations

## 🐛 Troubleshooting

### Common Issues

#### Singularity Not Found
```bash
# Error: Singularity is not installed or not in PATH
# Solution: Install Singularity
sudo apt-get install singularity-container  # Ubuntu/Debian
# Or use Docker backend by setting environment variable
export IGVER_NO_SINGULARITY=1
```

#### BAM Index Missing
```bash
# Warning: BAM index not found for sample.bam
# Solution: Create index files
samtools index sample.bam
```

#### API Key Issues
```bash
# Error: OpenAI API key not found
# Solution: Set in environment or .env file
export OPENAI_API_KEY=sk-your-key-here
# Or add to .env file
```

#### Model Deprecation
```bash
# Error: The model 'gpt-4-vision-preview' has been deprecated
# Solution: Update to gpt-4o (already fixed in main_igver_agent_fixed.py)
```

### Debug Mode

Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

agent = GenomicAIAgent(...)
```

## 📚 Advanced Usage

### Custom IGV Preferences

Create a custom IGV preferences file:
```text
# igv_prefs.txt
SAM.SHOW_SOFT_CLIPPED=true
SAM.SHADE_BASE_QUALITY=true
SAM.FILTER_DUPLICATES=false
```

Use in analysis:
```python
config = AnalysisConfig(
    igv_config="path/to/igv_prefs.txt"
)
```

### Batch Processing

Process multiple samples:
```python
import glob

# Find all BAM files
bam_files = glob.glob("data/*.bam")

# Process in batches
for i in range(0, len(bam_files), 2):
    batch = bam_files[i:i+2]
    results = agent.comprehensive_analysis(
        bam_files=batch,
        regions=regions,
        session_name=f"batch_{i//2}"
    )
```

### Custom AI Prompts

Modify the AI prompt for specific analysis needs:
```python
# Extend the AIGenomicInterpreter class
class CustomInterpreter(AIGenomicInterpreter):
    def analyze_screenshot(self, image_path, region, context=""):
        # Custom prompt for cancer genomics
        prompt = f"""
        Analyze this tumor/normal pair visualization for {region}.
        Focus on:
        1. Somatic variants with VAF calculation
        2. Loss of heterozygosity
        3. Copy number variations
        Context: {context}
        """
        # ... rest of the method
```

## 🔒 Security Considerations

- **API Keys**: Never commit API keys to version control. Use environment variables or `.env` files
- **Data Privacy**: Be aware that screenshots are sent to AI providers for analysis
- **HIPAA Compliance**: For clinical use, ensure proper de-identification of patient data
- **Resource Limits**: Set appropriate limits for batch processing to avoid API rate limits

## 📝 Development

### Project Structure
```
igver_agent/
├── main_igver_agent_fixed.py    # Main agent implementation
├── requirements.txt              # Python dependencies
├── setup_agent.sh               # Installation script
├── run_agent.sh                 # Convenience runner
├── .env.template                # Environment template
├── test_*.py                    # Test scripts
├── AGENT_REVIEW_FINDINGS.md     # Code review documentation
└── README.md                    # This file
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is part of the IGVer package. See the main IGVer license for details.

## 🙏 Acknowledgments

- IGV team for the Integrative Genomics Viewer
- OpenAI for GPT-4 vision capabilities
- Anthropic for Claude vision models
- The genomics community for continuous feedback

## 📮 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Contact the IGVer maintainers
- Check the [main IGVer documentation](../README.md)

## 🚦 Status

- ✅ Screenshot generation with Singularity/Docker
- ✅ OpenAI GPT-4o integration
- ✅ Anthropic Claude integration
- ✅ Multi-BAM support
- ✅ Tagged regions support
- ✅ HTML/JSON reporting
- ✅ Batch processing
- 🔄 VCF overlay support (planned)
- 🔄 Real-time monitoring (planned)

---

**Version**: 1.0.0  
**Last Updated**: August 2024  
**Maintainer**: IGVer Team