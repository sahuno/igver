# 🧬 IGVer Agent User Guide

## Quick Start for New Users

### 1. Installation (One-Time Setup)
```bash
# Run the automated setup
./setup_agent.sh

# This will:
# - Create a virtual environment
# - Install all dependencies
# - Set up configuration files
```

### 2. Choose Your Interface

#### 🌐 **Option A: Web Interface** (Easiest for Beginners)
```bash
# Start the web interface
./igver_agent --web

# Or use the launcher menu
./igver_agent
# Then choose option 1
```

**Features:**
- ✅ No command line needed
- ✅ Visual interface with buttons
- ✅ Drag-and-drop support
- ✅ Real-time progress updates
- ✅ Built-in examples

**How to use:**
1. Open browser at http://localhost:5000
2. Click "Test Data" for quick demo
3. Enter your BAM files and regions
4. Click "Start Analysis"
5. View results instantly

---

#### 💻 **Option B: Interactive CLI** (Power Users)
```bash
# Start interactive mode
./igver_agent --cli --interactive

# Or use the launcher menu
./igver_agent
# Then choose option 2
```

**Features:**
- ✅ Step-by-step guidance
- ✅ Auto-completion
- ✅ Colored output
- ✅ Progress bars
- ✅ Smart suggestions

**How to use:**
1. Follow the prompts
2. Select files and regions
3. Choose AI provider
4. View results

---

#### ⚡ **Option C: Command Line** (Advanced Users)
```bash
# Quick analysis
./igver_agent --cli -b sample.bam -r "chr1:1000-2000"

# With multiple files
./igver_agent --cli \
  -b tumor.bam normal.bam \
  -r "chr17:43044295-43045802" \
  --ai openai \
  --context "BRCA1 analysis"
```

---

## 📝 Common Workflows

### 1. Cancer Gene Analysis
```bash
# Interactive mode will guide you
./igver_agent --cli --interactive

# Or use web interface with "Cancer Genes" template
./igver_agent --web
```

**What it does:**
- Visualizes BRCA1, BRCA2, TP53, and other cancer genes
- AI identifies potential variants
- Generates clinical report

### 2. Quality Control Check
```bash
# Use QC template
./igver_agent --web
# Click "QC Regions" button

# Or command line
./igver_agent --cli \
  -b sample.bam \
  -r test_config.QUICK_TEST_REGIONS \
  --context "QC check"
```

**What it does:**
- Checks coverage uniformity
- Identifies technical issues
- Suggests improvements

### 3. Batch Processing
```bash
# Create a BAM list file
echo "sample1.bam
sample2.bam
sample3.bam" > bam_list.txt

# Create regions file
echo "chr1:1000-2000 region1
chr2:3000-4000 region2" > regions.txt

# Run batch
./igver_agent --cli \
  -b bam_list.txt \
  -r regions.txt \
  -o batch_results/
```

---

## 🎯 Tips for Best Results

### Setting Up API Keys

#### For OpenAI (GPT-4):
1. Get key from https://platform.openai.com/api-keys
2. Add to environment:
```bash
export OPENAI_API_KEY=sk-your-key-here
```
3. Or add to `.env` file:
```bash
echo "OPENAI_API_KEY=sk-your-key-here" > .env
```

#### For Testing (No API needed):
- Use `--ai mock` or select "Mock" in interface
- Perfect for testing without costs

### Input File Formats

#### BAM Files:
- Must have `.bai` index files
- Can use text file with paths:
```text
/path/to/sample1.bam
/path/to/sample2.bam
```

#### Regions:
- Simple format: `chr1:1000-2000`
- With tags: `chr1:1000-2000 my_variant`
- From BED file: `regions.bed`

---

## 🔧 Troubleshooting

### Common Issues & Solutions

| Problem | Solution |
|---------|----------|
| "Singularity not found" | Install: `sudo apt-get install singularity-container` |
| "BAM index missing" | Create: `samtools index your.bam` |
| "API key not found" | Set: `export OPENAI_API_KEY=your-key` |
| "Permission denied" | Make executable: `chmod +x igver_agent` |
| "Flask not installed" | Install: `pip install flask flask-cors` |

### Getting Help

1. **Built-in help:**
```bash
./igver_agent --help
./igver_agent --cli --help
```

2. **Check configuration:**
```bash
python test_config.py
```

3. **Run tests:**
```bash
python run_tests.py
```

---

## 🎨 Customization

### User Preferences
The agent saves your preferences in `~/.igver_agent_config.json`:

```json
{
  "default_genome": "hg38",
  "default_ai_provider": "openai",
  "default_output_dir": "~/igver_results",
  "auto_open_report": true,
  "verbose": false
}
```

### Custom Templates
Add your own region templates:

```python
# In test_config.py
MY_REGIONS = [
    "chr1:1000-2000",
    "chr2:3000-4000"
]
```

---

## 📊 Understanding Results

### Output Files
```
results/
├── session_name/
│   ├── chr1-1000-2000.png         # IGV screenshot
│   ├── analysis_results.json      # Complete data
│   └── report.html                # Visual report
```

### AI Analysis Sections
1. **Coverage Assessment** - Read depth analysis
2. **Alignment Quality** - Technical issues
3. **Variant Detection** - Potential mutations
4. **Clinical Relevance** - Medical significance
5. **Recommendations** - Next steps

### Success Indicators
- ✅ **Green**: Analysis successful
- ⚠️ **Yellow**: Warnings (check details)
- ❌ **Red**: Errors (see troubleshooting)

---

## 🚀 Advanced Features

### Custom AI Prompts
```python
# Modify context for specific analysis
context = """
Focus on:
1. Somatic vs germline variants
2. VAF > 5%
3. Known hotspots only
"""
```

### Parallel Processing
```bash
# Use multiple cores
export IGVER_PARALLEL=4
./igver_agent --cli -b many_samples.txt
```

### Remote Access (Web UI)
```bash
# Allow network access
python web_interface.py --host 0.0.0.0

# Access from another computer
http://server-ip:5000
```

---

## 📚 Examples Gallery

### Example 1: BRCA Testing
```bash
./igver_agent --cli \
  -b patient.bam \
  -r "chr17:43044295-43045802" \
  --ai openai \
  --context "BRCA1 pathogenic variant screening"
```

### Example 2: Tumor/Normal Comparison
```bash
./igver_agent --cli \
  -b tumor.bam normal.bam \
  -r cancer_genes.bed \
  --ai openai \
  --context "Somatic variant detection"
```

### Example 3: Family Trio
```bash
./igver_agent --cli \
  -b proband.bam mother.bam father.bam \
  -r disease_regions.txt \
  --context "Trio analysis for de novo variants"
```

---

## 🆘 Need More Help?

1. **Documentation:**
   - [README.md](README.md) - Overview
   - [API_REFERENCE.md](API_REFERENCE.md) - Technical details
   - [EXAMPLES.md](EXAMPLES.md) - Code examples

2. **Test Your Setup:**
```bash
# Quick test
python test_agent_logic_only.py

# Full test suite
python run_tests.py
```

3. **Check Logs:**
```bash
# View recent analyses
ls -la test_results/

# Check specific log
cat test_results/*/analysis_results.json
```

---

## 🎉 You're Ready!

Start with the web interface for the easiest experience:
```bash
./igver_agent --web
```

Or jump into interactive mode:
```bash
./igver_agent --cli --interactive
```

Happy analyzing! 🧬✨