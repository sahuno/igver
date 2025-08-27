# IGVer Agent Examples

## 📚 Complete Working Examples

### Example 1: Basic Cancer Genomics Analysis

```python
#!/usr/bin/env python3
"""
Analyze tumor/normal pairs for somatic variants
"""

from main_igver_agent_fixed import GenomicAIAgent, AnalysisConfig

# Configure for cancer genomics
config = AnalysisConfig(
    genome="hg38",
    output_format="png",
    max_panel_height=250,  # Taller panels for tumor/normal
    overlap_display="squish"
)

# Initialize agent
agent = GenomicAIAgent(
    singularity_image="docker://sahuno/igver:latest",
    output_base_dir="/results/cancer_analysis",
    config=config,
    ai_provider="openai"
)

# Define cancer gene hotspots
cancer_regions = [
    "chr17:43044295-43045802",   # BRCA1 exon 11
    "chr13:32315086-32400266",   # BRCA2 exon 10
    "chr9:21967752-21975098",    # CDKN2A
    "chr17:7571720-7579721",     # TP53
    "chr3:178936082-178938062"   # PIK3CA
]

region_tags = [
    "BRCA1_exon11",
    "BRCA2_exon10",
    "CDKN2A_full",
    "TP53_hotspot",
    "PIK3CA_kinase"
]

# Run analysis
results = agent.comprehensive_analysis(
    bam_files=["tumor.bam", "normal.bam"],
    regions=cancer_regions,
    region_tags=region_tags,
    session_name="cancer_panel",
    context="Somatic variant detection in cancer genes. Focus on VAF and tumor purity.",
    ai_analysis=True
)

# Print findings
print(f"Analysis complete: {results['summary']['overall_status']}")
for region, analysis in results['ai_analyses'].items():
    if 'variant' in analysis.get('analysis', '').lower():
        print(f"⚠️  Potential variant in {region}")
```

### Example 2: Hereditary Disease Screening

```python
#!/usr/bin/env python3
"""
Screen for hereditary disease variants across multiple samples
"""

from main_igver_agent_fixed import GenomicAIAgent, AnalysisConfig
import json

def screen_family_trio(proband_bam, mother_bam, father_bam, disease_regions):
    """Screen a family trio for hereditary variants"""
    
    config = AnalysisConfig(
        genome="hg38",
        output_format="png",
        max_panel_height=300  # Show all three samples
    )
    
    agent = GenomicAIAgent(
        config=config,
        ai_provider="openai"
    )
    
    # Analyze trio
    results = agent.comprehensive_analysis(
        bam_files=[proband_bam, mother_bam, father_bam],
        regions=disease_regions,
        session_name="family_trio",
        context="""
        Family trio analysis for hereditary disease.
        Sample order: Proband (affected), Mother, Father.
        Look for:
        1. De novo variants in proband
        2. Compound heterozygous variants
        3. Homozygous variants in proband
        4. X-linked variants (if proband is male)
        """,
        ai_analysis=True
    )
    
    # Identify inheritance patterns
    for region, analysis in results['ai_analyses'].items():
        analysis_text = analysis.get('analysis', '')
        
        if 'de novo' in analysis_text.lower():
            print(f"🔴 Possible de novo variant: {region}")
        elif 'homozygous' in analysis_text.lower():
            print(f"🟡 Homozygous variant: {region}")
        elif 'heterozygous' in analysis_text.lower():
            print(f"🔵 Heterozygous variant: {region}")
    
    return results

# Example usage
disease_regions = [
    "chr19:13049414-13049714",  # CALR
    "chr1:115256420-115256720",  # NRAS
    "chr4:55593464-55593764"     # KIT
]

results = screen_family_trio(
    proband_bam="proband.bam",
    mother_bam="mother.bam", 
    father_bam="father.bam",
    disease_regions=disease_regions
)
```

### Example 3: Batch Processing with Progress Tracking

```python
#!/usr/bin/env python3
"""
Process multiple samples with progress tracking
"""

from main_igver_agent_fixed import GenomicAIAgent, AnalysisConfig
from pathlib import Path
import glob
from tqdm import tqdm
import json

def batch_process_samples(sample_dir, regions_file, output_dir):
    """Process all BAM files in a directory"""
    
    # Find all BAM files
    bam_files = glob.glob(f"{sample_dir}/*.bam")
    print(f"Found {len(bam_files)} BAM files")
    
    # Load regions
    with open(regions_file) as f:
        regions = [line.strip() for line in f if line.strip()]
    print(f"Loaded {len(regions)} regions")
    
    # Initialize agent
    agent = GenomicAIAgent(
        output_base_dir=output_dir,
        ai_provider="openai"
    )
    
    # Process each BAM file
    all_results = {}
    
    for bam_file in tqdm(bam_files, desc="Processing samples"):
        sample_name = Path(bam_file).stem
        
        try:
            results = agent.comprehensive_analysis(
                bam_files=[bam_file],
                regions=regions,
                session_name=sample_name,
                context=f"Quality control for sample {sample_name}",
                ai_analysis=True
            )
            
            # Store key metrics
            all_results[sample_name] = {
                'success_rate': results['summary']['success_rate'],
                'screenshots': len(results['screenshots']),
                'issues': []
            }
            
            # Check for quality issues
            for region, analysis in results['ai_analyses'].items():
                if 'poor quality' in analysis.get('analysis', '').lower():
                    all_results[sample_name]['issues'].append(region)
                    
        except Exception as e:
            print(f"Error processing {sample_name}: {e}")
            all_results[sample_name] = {'error': str(e)}
    
    # Generate summary report
    summary_file = Path(output_dir) / "batch_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\nBatch processing complete. Summary saved to {summary_file}")
    
    # Print samples with issues
    for sample, data in all_results.items():
        if data.get('issues'):
            print(f"⚠️  {sample}: Issues in {len(data['issues'])} regions")
    
    return all_results

# Run batch processing
results = batch_process_samples(
    sample_dir="/data/samples",
    regions_file="qc_regions.txt",
    output_dir="/results/batch_qc"
)
```

### Example 4: Custom AI Analysis for Structural Variants

```python
#!/usr/bin/env python3
"""
Specialized analysis for structural variant detection
"""

from main_igver_agent_fixed import GenomicAIAgent, AnalysisConfig
import re

class StructuralVariantAgent(GenomicAIAgent):
    """Extended agent for SV detection"""
    
    def analyze_for_sv(self, bam_files, breakpoint_regions):
        """Analyze potential breakpoint regions for SVs"""
        
        # Custom context for SV detection
        sv_context = """
        Structural variant breakpoint analysis. Look for:
        1. Split reads (soft-clipped reads at breakpoints)
        2. Discordant read pairs (abnormal insert sizes or orientations)
        3. Read depth changes (duplications or deletions)
        4. Reads mapping to different chromosomes (translocations)
        5. Inverted read orientations (inversions)
        
        Report the likely SV type and confidence level.
        """
        
        results = self.comprehensive_analysis(
            bam_files=bam_files,
            regions=breakpoint_regions,
            session_name="sv_analysis",
            context=sv_context,
            ai_analysis=True
        )
        
        # Parse SV predictions from AI analysis
        sv_calls = []
        
        for region, analysis in results['ai_analyses'].items():
            text = analysis.get('analysis', '')
            
            # Extract SV type predictions
            sv_type = None
            confidence = "low"
            
            if re.search(r'deletion|loss', text, re.I):
                sv_type = "DELETION"
            elif re.search(r'duplication|gain', text, re.I):
                sv_type = "DUPLICATION"
            elif re.search(r'inversion|inverted', text, re.I):
                sv_type = "INVERSION"
            elif re.search(r'translocation|different chromosome', text, re.I):
                sv_type = "TRANSLOCATION"
            
            if re.search(r'high confidence|clearly|obvious', text, re.I):
                confidence = "high"
            elif re.search(r'moderate|likely|probable', text, re.I):
                confidence = "medium"
            
            if sv_type:
                sv_calls.append({
                    'region': region,
                    'type': sv_type,
                    'confidence': confidence,
                    'evidence': text[:200]
                })
        
        return sv_calls

# Use the SV agent
config = AnalysisConfig(
    genome="hg38",
    max_panel_height=400,  # Taller to see read patterns
    overlap_display="expand"  # Show all reads
)

sv_agent = StructuralVariantAgent(
    config=config,
    ai_provider="openai"
)

# Analyze known SV breakpoints
breakpoints = [
    "chr8:128747680-128748680",  # MYC translocation breakpoint
    "chr9:22000000-22100000",    # CDKN2A deletion
    "chr17:41196312-41277500"    # BRCA1 large deletion
]

sv_calls = sv_agent.analyze_for_sv(
    bam_files=["sample.bam"],
    breakpoint_regions=breakpoints
)

# Report findings
for sv in sv_calls:
    print(f"{sv['type']} detected at {sv['region']} ({sv['confidence']} confidence)")
    print(f"  Evidence: {sv['evidence']}\n")
```

### Example 5: Integration with Clinical Databases

```python
#!/usr/bin/env python3
"""
Integrate with ClinVar for clinical interpretation
"""

from main_igver_agent_fixed import GenomicAIAgent, AnalysisConfig
import requests
import xml.etree.ElementTree as ET

def get_clinvar_info(chrom, start, end):
    """Query ClinVar for variants in region"""
    
    # ClinVar E-utilities API
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    # Search for variants in region
    search_term = f"{chrom}[Chromosome] AND {start}:{end}[Base Position]"
    search_url = f"{base_url}/esearch.fcgi"
    params = {
        'db': 'clinvar',
        'term': search_term,
        'retmax': 10,
        'retmode': 'xml'
    }
    
    try:
        response = requests.get(search_url, params=params)
        root = ET.fromstring(response.text)
        
        # Extract variant IDs
        ids = [id_elem.text for id_elem in root.findall('.//Id')]
        
        if ids:
            # Fetch variant details
            fetch_url = f"{base_url}/esummary.fcgi"
            params = {
                'db': 'clinvar',
                'id': ','.join(ids),
                'retmode': 'xml'
            }
            response = requests.get(fetch_url, params=params)
            
            # Parse clinical significance
            variants = []
            root = ET.fromstring(response.text)
            for doc_sum in root.findall('.//DocumentSummary'):
                title = doc_sum.find('.//title').text if doc_sum.find('.//title') is not None else ""
                sig = doc_sum.find('.//clinical_significance').text if doc_sum.find('.//clinical_significance') is not None else ""
                variants.append({
                    'title': title,
                    'significance': sig
                })
            
            return variants
    except Exception as e:
        print(f"ClinVar query failed: {e}")
    
    return []

def analyze_with_clinical_context(agent, bam_files, regions):
    """Analyze regions with ClinVar annotation"""
    
    # Get ClinVar data for each region
    clinical_context = []
    
    for region in regions:
        # Parse region
        chrom, coords = region.split(':')
        start, end = coords.split('-')
        
        # Query ClinVar
        clinvar_variants = get_clinvar_info(chrom, start, end)
        
        if clinvar_variants:
            context = f"Known variants in region: "
            for var in clinvar_variants[:3]:  # Top 3
                context += f"{var['title']} ({var['significance']}); "
            clinical_context.append(context)
        else:
            clinical_context.append("No known pathogenic variants in ClinVar")
    
    # Run analysis with clinical context
    full_context = "Clinical variant analysis with ClinVar annotations.\n"
    full_context += "\n".join([f"{r}: {c}" for r, c in zip(regions, clinical_context)])
    
    results = agent.comprehensive_analysis(
        bam_files=bam_files,
        regions=regions,
        context=full_context,
        session_name="clinical_analysis",
        ai_analysis=True
    )
    
    # Combine IGV analysis with ClinVar data
    for region in regions:
        print(f"\n{'='*60}")
        print(f"Region: {region}")
        
        # ClinVar info
        chrom, coords = region.split(':')
        start, end = coords.split('-')
        variants = get_clinvar_info(chrom, start, end)
        
        if variants:
            print("\nClinVar variants:")
            for var in variants:
                print(f"  • {var['title']}")
                print(f"    Significance: {var['significance']}")
        
        # AI analysis
        if region in results['ai_analyses']:
            analysis = results['ai_analyses'][region]
            print(f"\nAI Analysis:")
            print(analysis.get('analysis', '')[:500])
    
    return results

# Example usage
agent = GenomicAIAgent(ai_provider="openai")

clinical_regions = [
    "chr7:117559590-117559593",  # CFTR F508del
    "chr17:43091983-43091986",   # BRCA1 185delAG
    "chr11:534242-534248"        # HBB sickle cell
]

results = analyze_with_clinical_context(
    agent=agent,
    bam_files=["patient.bam"],
    regions=clinical_regions
)
```

### Example 6: Quality Control Pipeline

```python
#!/usr/bin/env python3
"""
Comprehensive QC pipeline for sequencing data
"""

from main_igver_agent_fixed import GenomicAIAgent, AnalysisConfig
import json
from datetime import datetime

class QualityControlPipeline:
    """QC pipeline using IGVer agent"""
    
    def __init__(self, output_dir):
        self.agent = GenomicAIAgent(
            output_base_dir=output_dir,
            config=AnalysisConfig(
                genome="hg38",
                max_panel_height=200
            ),
            ai_provider="openai"
        )
        self.qc_regions = self._get_qc_regions()
    
    def _get_qc_regions(self):
        """Standard QC regions across the genome"""
        return {
            'high_gc': [
                "chr19:58858172-58864865",  # High GC region
                "chr17:41196312-41277500"   # BRCA1 (high GC)
            ],
            'low_gc': [
                "chr4:1000000-1010000",     # Low GC region
                "chr13:32889611-32973805"   # BRCA2 (moderate GC)
            ],
            'repetitive': [
                "chr1:121184000-121185000",  # ALU repeat region
                "chrY:10000-20000"           # Y chromosome repeats
            ],
            'exonic': [
                "chr12:112450394-112450500",  # ALDH2 exon
                "chr7:117559590-117559690"    # CFTR exon
            ],
            'intronic': [
                "chr2:215595000-215600000",   # BARD1 intron
                "chr17:7675000-7676000"       # TP53 intron
            ]
        }
    
    def run_qc(self, bam_file, sample_name):
        """Run comprehensive QC on a BAM file"""
        
        qc_results = {
            'sample': sample_name,
            'timestamp': datetime.now().isoformat(),
            'metrics': {},
            'issues': [],
            'recommendations': []
        }
        
        # Check each QC region category
        for category, regions in self.qc_regions.items():
            print(f"Checking {category} regions...")
            
            results = self.agent.comprehensive_analysis(
                bam_files=[bam_file],
                regions=regions,
                session_name=f"{sample_name}_{category}",
                context=f"QC analysis for {category} regions. Assess coverage uniformity and quality.",
                ai_analysis=True
            )
            
            # Extract QC metrics from AI analysis
            category_issues = []
            
            for region, analysis in results['ai_analyses'].items():
                text = analysis.get('analysis', '')
                
                # Check for common QC issues
                if 'low coverage' in text.lower():
                    category_issues.append(f"Low coverage in {region}")
                if 'uneven' in text.lower() or 'dropout' in text.lower():
                    category_issues.append(f"Coverage dropout in {region}")
                if 'high duplication' in text.lower():
                    category_issues.append(f"High duplication in {region}")
                if 'poor quality' in text.lower():
                    category_issues.append(f"Poor quality in {region}")
            
            qc_results['metrics'][category] = {
                'regions_checked': len(regions),
                'issues_found': len(category_issues),
                'screenshots_generated': len(results['screenshots'])
            }
            
            if category_issues:
                qc_results['issues'].extend(category_issues)
        
        # Generate recommendations
        if any('low coverage' in issue.lower() for issue in qc_results['issues']):
            qc_results['recommendations'].append("Consider resequencing for better coverage")
        
        if any('high duplication' in issue.lower() for issue in qc_results['issues']):
            qc_results['recommendations'].append("Review PCR conditions to reduce duplicates")
        
        if any('high_gc' in k and v['issues_found'] > 0 
               for k, v in qc_results['metrics'].items()):
            qc_results['recommendations'].append("Optimize protocol for high-GC regions")
        
        # Overall QC status
        total_issues = sum(m['issues_found'] for m in qc_results['metrics'].values())
        if total_issues == 0:
            qc_results['status'] = 'PASS'
        elif total_issues <= 2:
            qc_results['status'] = 'PASS_WITH_WARNINGS'
        else:
            qc_results['status'] = 'FAIL'
        
        return qc_results
    
    def generate_qc_report(self, qc_results, output_file):
        """Generate QC report"""
        
        with open(output_file, 'w') as f:
            f.write("# Quality Control Report\n\n")
            f.write(f"**Sample:** {qc_results['sample']}\n")
            f.write(f"**Date:** {qc_results['timestamp']}\n")
            f.write(f"**Status:** {qc_results['status']}\n\n")
            
            f.write("## Metrics Summary\n\n")
            for category, metrics in qc_results['metrics'].items():
                f.write(f"### {category.upper()}\n")
                f.write(f"- Regions checked: {metrics['regions_checked']}\n")
                f.write(f"- Issues found: {metrics['issues_found']}\n\n")
            
            if qc_results['issues']:
                f.write("## Issues Detected\n\n")
                for issue in qc_results['issues']:
                    f.write(f"- {issue}\n")
                f.write("\n")
            
            if qc_results['recommendations']:
                f.write("## Recommendations\n\n")
                for rec in qc_results['recommendations']:
                    f.write(f"- {rec}\n")
        
        # Also save JSON version
        json_file = output_file.replace('.md', '.json')
        with open(json_file, 'w') as f:
            json.dump(qc_results, f, indent=2)
        
        print(f"QC report saved to {output_file}")
        return output_file

# Run QC pipeline
pipeline = QualityControlPipeline(output_dir="/results/qc")

qc_results = pipeline.run_qc(
    bam_file="sample.bam",
    sample_name="SAMPLE_001"
)

report_file = pipeline.generate_qc_report(
    qc_results,
    output_file="/results/qc/SAMPLE_001_qc_report.md"
)

print(f"QC Status: {qc_results['status']}")
```

## 🎯 Common Use Cases

### Filtering Results

```python
# Filter for high-confidence variants only
high_confidence = {
    region: analysis 
    for region, analysis in results['ai_analyses'].items()
    if analysis.get('confidence', 0) > 0.8
}
```

### Comparing Multiple Samples

```python
# Compare variant calls across samples
def compare_samples(sample_results):
    all_variants = {}
    
    for sample_name, results in sample_results.items():
        for region, analysis in results['ai_analyses'].items():
            if 'variant' in analysis.get('analysis', '').lower():
                if region not in all_variants:
                    all_variants[region] = []
                all_variants[region].append(sample_name)
    
    # Find shared variants
    shared = {k: v for k, v in all_variants.items() if len(v) > 1}
    return shared
```

### Error Recovery

```python
# Retry failed regions
def retry_failed_regions(agent, results, bam_files):
    failed_regions = []
    
    for region in results['input_summary']['regions']:
        if region not in results['screenshots']:
            failed_regions.append(region)
    
    if failed_regions:
        print(f"Retrying {len(failed_regions)} failed regions...")
        retry_results = agent.comprehensive_analysis(
            bam_files=bam_files,
            regions=failed_regions,
            session_name="retry",
            ai_analysis=False  # Skip AI to save time
        )
        return retry_results
    return None
```

### Custom Output Formats

```python
# Export to VCF-like format
def export_to_vcf_format(results, output_file):
    with open(output_file, 'w') as f:
        # VCF header
        f.write("##fileformat=VCFv4.3\n")
        f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
        
        for region, analysis in results['ai_analyses'].items():
            # Parse region
            chrom, coords = region.split(':')
            start, _ = coords.split('-')
            
            # Extract variant info from AI analysis (simplified)
            if 'variant' in analysis.get('analysis', '').lower():
                f.write(f"{chrom}\t{start}\t.\t.\t.\t.\tPASS\tAI_DETECTED\n")
```

---

These examples demonstrate the flexibility and power of the IGVer Agent for various genomic analysis workflows. Customize them for your specific needs!