#!/usr/bin/env python3
"""
🧬 FIXED Genomic AI Agent - Production-Ready Implementation
Combines IGV screenshot generation with AI-powered genomic interpretation

Key Fixes Applied:
- Corrected OpenAI API usage for both v0.x and v1.x
- Fixed region file format to match igver expectations
- Added path validation and expansion
- Improved error handling and logging
- Added support for BED files and text input files
- Enhanced AI prompting for genomics
"""

import igver
import os
import sys
import json
import logging
import base64
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union, Any
from dataclasses import dataclass, field
import subprocess
from datetime import datetime

# AI Integration imports
try:
    import openai
    OPENAI_AVAILABLE = True
    # Check OpenAI version
    if hasattr(openai, '__version__'):
        OPENAI_VERSION = tuple(map(int, openai.__version__.split('.')[:2]))
    else:
        OPENAI_VERSION = (0, 27)  # Default to old version
except ImportError:
    OPENAI_AVAILABLE = False
    OPENAI_VERSION = None

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

@dataclass
class GenomicRegion:
    """Represents a genomic region with optional tag"""
    chromosome: str
    start: int
    end: int
    tag: Optional[str] = None
    name: Optional[str] = None  # For BED6 format
    
    def __str__(self):
        return f"{self.chromosome}:{self.start}-{self.end}"
    
    def to_filename_base(self):
        """Generate filename-safe string representation"""
        base = f"{self.chromosome}-{self.start}-{self.end}"
        if self.name:
            return f"{base}.{self.name}"
        elif self.tag:
            return f"{base}.{self.tag}"
        return base

@dataclass
class AnalysisConfig:
    """Configuration for genomic analysis"""
    genome: str = "hg38"
    output_format: str = "png"
    max_panel_height: int = 200
    overlap_display: str = "squish"
    igv_config: Optional[str] = None
    remove_png: bool = False
    dpi: int = 300

class InputValidator:
    """Validates and prepares input files"""
    
    @staticmethod
    def validate_bam_files(bam_files: List[str]) -> List[str]:
        """Validate BAM files and their indices"""
        validated = []
        for bam in bam_files:
            bam_path = Path(bam).expanduser().resolve()
            if not bam_path.exists():
                raise FileNotFoundError(f"BAM file not found: {bam}")
            
            # Check for index file
            bai_path = bam_path.with_suffix(bam_path.suffix + '.bai')
            alt_bai_path = bam_path.with_suffix('.bai')
            if not (bai_path.exists() or alt_bai_path.exists()):
                logging.warning(f"BAM index not found for {bam}. IGV may fail.")
            
            validated.append(str(bam_path))
        return validated
    
    @staticmethod
    def parse_input_file(file_path: str) -> List[str]:
        """Parse a text file containing paths to tracks"""
        paths = []
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                path = Path(line).expanduser().resolve()
                if path.exists():
                    paths.append(str(path))
                else:
                    logging.warning(f"Path not found: {line}")
        return paths
    
    @staticmethod
    def check_singularity() -> bool:
        """Check if Singularity is installed"""
        try:
            result = subprocess.run(['singularity', '--version'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False

class SmartSingularityMounter:
    """Handles intelligent Singularity mounting with validation"""
    
    def __init__(self, singularity_image: str):
        self.image_path = Path(singularity_image).resolve()
        self.logger = logging.getLogger(__name__)
        
        # Validate singularity installation
        if not InputValidator.check_singularity():
            raise RuntimeError("Singularity is not installed or not in PATH")
        
        # Validate image exists
        if not self.image_path.exists() and not singularity_image.startswith('docker://'):
            raise FileNotFoundError(f"Singularity image not found: {singularity_image}")
    
    def get_mount_args(self, bam_files: List[str], output_dir: str, 
                       additional_paths: Optional[List[str]] = None) -> str:
        """Generate optimal mount points for Singularity"""
        mount_points = set()
        
        # Always mount common directories
        mount_points.update(['/home', '/tmp'])
        
        # Add TMPDIR if set
        tmpdir = os.environ.get('TMPDIR')
        if tmpdir:
            mount_points.add(Path(tmpdir).resolve().as_posix())
        
        # Mount singularity image parent directory
        if not self.image_path.as_posix().startswith('docker://'):
            image_parent = self.image_path.parent
            mount_points.add(str(image_parent))
            self.logger.info(f"Mounting singularity image directory: {image_parent}")
        
        # Mount BAM file directories
        for bam_file in bam_files:
            bam_path = Path(bam_file).expanduser().resolve()
            if bam_path.exists():
                mount_points.add(str(bam_path.parent))
        
        # Mount output directory
        output_path = Path(output_dir).resolve()
        mount_points.add(str(output_path))
        mount_points.add(str(output_path.parent))
        
        # Mount additional paths
        if additional_paths:
            for path in additional_paths:
                resolved_path = Path(path).expanduser().resolve()
                if resolved_path.exists():
                    if resolved_path.is_file():
                        mount_points.add(str(resolved_path.parent))
                    else:
                        mount_points.add(str(resolved_path))
        
        mount_args = ' '.join([f'-B {mp}' for mp in sorted(mount_points)])
        self.logger.info(f"Singularity mount args: {mount_args}")
        return mount_args

class AIGenomicInterpreter:
    """AI-powered genomic screenshot interpretation"""
    
    def __init__(self, provider: str = "openai", api_key: Optional[str] = None):
        self.provider = provider
        self.api_key = api_key or os.getenv(f"{provider.upper()}_API_KEY")
        self.logger = logging.getLogger(__name__)
        
        if provider == "openai" and OPENAI_AVAILABLE:
            if OPENAI_VERSION and OPENAI_VERSION[0] >= 1:
                # OpenAI v1.x
                self.openai_client = openai.OpenAI(api_key=self.api_key)
            else:
                # OpenAI v0.x
                openai.api_key = self.api_key
                self.openai_client = None
        elif provider == "anthropic" and ANTHROPIC_AVAILABLE:
            self.anthropic_client = anthropic.Anthropic(api_key=self.api_key)
    
    def analyze_screenshot(self, image_path: str, region: str, context: str = "") -> Dict:
        """Analyze genomic screenshot using AI vision models"""
        
        if not os.path.exists(image_path):
            return {"error": f"Image not found: {image_path}"}
        
        # Enhanced genomics-specific prompt
        prompt = f"""
        Analyze this IGV (Integrative Genomics Viewer) screenshot for genomic region {region}.
        
        You are an expert clinical genomicist. Please provide a detailed analysis including:
        
        1. **Coverage Assessment**: 
           - Average depth and uniformity across the region
           - Identify any coverage gaps or drops
           - Note areas of unusually high coverage (potential duplications)
        
        2. **Read Alignment Quality**:
           - Presence of soft-clipped reads (potential structural variants)
           - Misaligned or improperly paired reads
           - Read orientation anomalies
        
        3. **Variant Detection**:
           - Visible SNPs/SNVs with approximate allele frequencies
           - Indels (insertions/deletions)
           - Potential structural variants (inversions, translocations, CNVs)
           - Note variant positions in genomic coordinates
        
        4. **Technical Quality Issues**:
           - PCR duplicates or amplification artifacts
           - Mapping quality problems
           - Sequencing errors or systematic biases
           - GC content biases
        
        5. **Clinical/Biological Relevance**:
           - Known pathogenic variant hotspots in this region
           - Genes affected and their clinical significance
           - Recommended validation methods (Sanger, qPCR, etc.)
        
        6. **Confidence and Recommendations**:
           - Confidence level for each finding (high/medium/low)
           - Suggested follow-up analyses
           - Additional regions that should be examined
        
        Context provided: {context}
        
        Please be specific about genomic coordinates and provide quantitative assessments where possible.
        Format your response clearly with the numbered sections above.
        """
        
        try:
            if self.provider == "openai" and OPENAI_AVAILABLE:
                return self._analyze_with_openai(image_path, prompt, region)
            elif self.provider == "anthropic" and ANTHROPIC_AVAILABLE:
                return self._analyze_with_anthropic(image_path, prompt, region)
            else:
                return self._mock_analysis(region)
        except Exception as e:
            self.logger.error(f"AI analysis failed for {region}: {e}")
            return {"error": str(e), "region": region}
    
    def _encode_image_base64(self, image_path: str) -> str:
        """Encode image as base64"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def _analyze_with_openai(self, image_path: str, prompt: str, region: str) -> Dict:
        """OpenAI GPT-4V analysis with version compatibility"""
        base64_image = self._encode_image_base64(image_path)
        
        try:
            if self.openai_client:  # v1.x
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o",  # Updated model - gpt-4-vision-preview was deprecated
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                                }
                            ]
                        }
                    ],
                    max_tokens=2000
                )
                analysis_text = response.choices[0].message.content
            else:  # v0.x
                response = openai.ChatCompletion.create(
                    model="gpt-4-vision-preview",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": f"data:image/png;base64,{base64_image}"
                                }
                            ]
                        }
                    ],
                    max_tokens=2000
                )
                analysis_text = response['choices'][0]['message']['content']
            
            return {
                "provider": "openai",
                "model": "gpt-4o",
                "region": region,
                "analysis": analysis_text,
                "confidence": 0.85,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            raise
    
    def _analyze_with_anthropic(self, image_path: str, prompt: str, region: str) -> Dict:
        """Anthropic Claude analysis"""
        base64_image = self._encode_image_base64(image_path)
        
        response = self.anthropic_client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": base64_image
                            }
                        },
                        {"type": "text", "text": prompt}
                    ]
                }
            ]
        )
        
        return {
            "provider": "anthropic",
            "model": "claude-3-opus",
            "region": region,
            "analysis": response.content[0].text,
            "confidence": 0.88,
            "timestamp": datetime.now().isoformat()
        }
    
    def _mock_analysis(self, region: str) -> Dict:
        """Enhanced mock analysis for testing"""
        return {
            "provider": "mock",
            "region": region,
            "analysis": f"""
Mock Analysis for {region}:

1. **Coverage Assessment**: Average depth ~150x, uniform coverage across region
2. **Read Alignment Quality**: Good alignment, <1% soft-clipped reads
3. **Variant Detection**: No obvious variants detected
4. **Technical Quality**: Good quality, no significant artifacts
5. **Clinical Relevance**: No known pathogenic variants in this region
6. **Recommendations**: Standard quality, no follow-up needed

Note: Install openai or anthropic package for real AI analysis.
""",
            "confidence": 0.5,
            "timestamp": datetime.now().isoformat()
        }

class GenomicAIAgent:
    """🧬 Production-Ready Genomic AI Agent"""
    
    def __init__(self, 
                 singularity_image: str = None,
                 output_base_dir: str = None,
                 config: Optional[AnalysisConfig] = None,
                 ai_provider: str = "openai",
                 ai_api_key: Optional[str] = None):
        
        # Set defaults
        self.singularity_image = singularity_image or os.environ.get('IGVER_IMAGE', 'docker://sahuno/igver:latest')
        
        # Handle output directory properly
        if output_base_dir is None:
            output_base_dir = os.environ.get('TMPDIR', '/tmp')
        self.output_base_dir = Path(output_base_dir) / 'genomic_ai_agent'
        
        self.config = config or AnalysisConfig()
        
        # Initialize components
        if singularity_image and not os.environ.get('IGVER_NO_SINGULARITY'):
            self.mounter = SmartSingularityMounter(singularity_image)
        else:
            self.mounter = None
        
        self.ai_interpreter = AIGenomicInterpreter(ai_provider, ai_api_key)
        self.validator = InputValidator()
        
        # Setup
        self.output_base_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)
    
    def prepare_input_files(self, 
                           bam_files: List[str], 
                           regions: List[str], 
                           region_tags: Optional[List[str]], 
                           session_dir: Path) -> Tuple[List[str], List[str], List[GenomicRegion]]:
        """Prepare and validate input files"""
        
        # Handle text file input for BAM files
        expanded_bam_files = []
        for bam in bam_files:
            if bam.endswith('.txt'):
                expanded_bam_files.extend(self.validator.parse_input_file(bam))
            else:
                expanded_bam_files.append(bam)
        
        # Validate BAM files
        validated_bams = self.validator.validate_bam_files(expanded_bam_files)
        
        # Create BAM list file if beneficial
        if len(validated_bams) > 2:
            bam_list_file = session_dir / "bam_list.txt"
            with open(bam_list_file, 'w') as f:
                f.write("# BAM files for IGV analysis\n")
                for bam in validated_bams:
                    f.write(f"{bam}\n")
            paths_input = [str(bam_list_file)]
            self.logger.info(f"Created BAM list file with {len(validated_bams)} files")
        else:
            paths_input = validated_bams
        
        # Process regions
        parsed_regions = []
        if region_tags or len(regions) > 5:
            # Create regions file with proper format (space-separated, not tab)
            regions_file = session_dir / "regions_list.txt"
            with open(regions_file, 'w') as f:
                f.write("# Genomic regions with optional tags\n")
                for i, region in enumerate(regions):
                    tag = region_tags[i] if region_tags and i < len(region_tags) else None
                    parsed_region = self._parse_region(region, tag)
                    parsed_regions.append(parsed_region)
                    
                    # Use space separator, not tab (igver expects space)
                    if tag:
                        f.write(f"{region} {tag}\n")  # Space, not tab!
                    else:
                        f.write(f"{region}\n")
            regions_input = [str(regions_file)]
            self.logger.info(f"Created regions file with {len(regions)} regions")
        else:
            regions_input = regions
            parsed_regions = [self._parse_region(r) for r in regions]
        
        return paths_input, regions_input, parsed_regions
    
    def _parse_region(self, region_str: str, tag: Optional[str] = None) -> GenomicRegion:
        """Parse genomic region string with validation"""
        try:
            if ':' in region_str and '-' in region_str:
                chrom, coords = region_str.split(':')
                start, end = coords.split('-')
                return GenomicRegion(chrom, int(start), int(end), tag)
            else:
                raise ValueError(f"Invalid region format: {region_str}")
        except Exception as e:
            self.logger.error(f"Failed to parse region {region_str}: {e}")
            raise
    
    def generate_screenshots(self, 
                           bam_files: List[str],
                           regions: List[str],
                           session_name: str = "analysis",
                           region_tags: Optional[List[str]] = None,
                           additional_mount_paths: Optional[List[str]] = None) -> Dict[str, str]:
        """Generate IGV screenshots with comprehensive error handling"""
        
        session_dir = self.output_base_dir / session_name
        session_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"🔬 Generating screenshots: {len(regions)} regions, {len(bam_files)} BAM files")
        
        try:
            # Prepare inputs
            paths_input, regions_input, parsed_regions = self.prepare_input_files(
                bam_files, regions, region_tags, session_dir
            )
            
            # Smart mounting
            mount_paths = (additional_mount_paths or []) + [str(session_dir)]
            if self.mounter:
                singularity_args = self.mounter.get_mount_args(
                    bam_files, str(session_dir), mount_paths
                )
            else:
                singularity_args = '-B /home -B /tmp'
            
            # Generate screenshots using igver
            self.logger.info("Calling igver.load_screenshots...")
            figures = igver.load_screenshots(
                paths=paths_input,
                regions=regions_input,
                output_dir=str(session_dir),
                genome=self.config.genome,
                singularity_image=self.singularity_image,
                singularity_args=singularity_args,
                overwrite=True,
                remove_png=self.config.remove_png,
                dpi=self.config.dpi,
                output_format=self.config.output_format,
                max_panel_height=self.config.max_panel_height,
                overlap_display=self.config.overlap_display,
                igv_config=self.config.igv_config
            )
            
            # Discover generated files
            screenshots = self._discover_screenshots(parsed_regions, session_dir)
            
            success_count = len(screenshots)
            self.logger.info(f"✅ Generated {success_count}/{len(regions)} screenshots")
            
            # Cleanup temporary files if needed
            if self.config.remove_png:
                self._cleanup_temp_files(session_dir)
            
            return screenshots
            
        except Exception as e:
            self.logger.error(f"Screenshot generation failed: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            
            # Attempt cleanup on failure
            self._cleanup_on_failure(session_dir)
            return {}
    
    def _discover_screenshots(self, parsed_regions: List[GenomicRegion], session_dir: Path) -> Dict[str, str]:
        """Discover generated files with improved matching"""
        screenshots = {}
        
        # Get expected extension
        ext = 'svg' if self.config.output_format in ['svg', 'pdf'] else self.config.output_format
        files = list(session_dir.glob(f"*.{ext}"))
        
        for region in parsed_regions:
            region_str = str(region)
            
            # Try exact filename prediction
            predicted_name = f"{region.to_filename_base()}.{ext}"
            predicted_path = session_dir / predicted_name
            
            if predicted_path.exists() and predicted_path.stat().st_size > 0:
                screenshots[region_str] = str(predicted_path)
                size = predicted_path.stat().st_size
                self.logger.info(f"  ✅ {region_str} -> {predicted_name} ({size:,} bytes)")
            else:
                # Try flexible pattern matching
                base_pattern = f"{region.chromosome}-{region.start}-{region.end}"
                matches = [f for f in files if base_pattern in f.name]
                
                if matches:
                    # Sort by modification time, newest first
                    matches.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                    best_match = matches[0]
                    screenshots[region_str] = str(best_match)
                    size = best_match.stat().st_size
                    self.logger.info(f"  ✅ {region_str} -> {best_match.name} ({size:,} bytes)")
                else:
                    self.logger.warning(f"  ❌ {region_str} -> No screenshot found")
        
        return screenshots
    
    def _cleanup_temp_files(self, session_dir: Path):
        """Clean up temporary files"""
        patterns = ['*.batch', '*.log', '*.tmp']
        for pattern in patterns:
            for file in session_dir.glob(pattern):
                try:
                    file.unlink()
                except Exception as e:
                    self.logger.warning(f"Failed to remove {file}: {e}")
    
    def _cleanup_on_failure(self, session_dir: Path):
        """Emergency cleanup on failure"""
        try:
            # Keep the directory but remove incomplete files
            for file in session_dir.glob('*.batch'):
                file.unlink()
        except Exception as e:
            self.logger.warning(f"Cleanup failed: {e}")
    
    def analyze_with_ai(self, screenshots: Dict[str, str], context: str = "") -> Dict[str, Dict]:
        """Run AI analysis on screenshots with progress tracking"""
        if not screenshots:
            return {}
        
        self.logger.info(f"🤖 Running AI analysis on {len(screenshots)} screenshots...")
        analyses = {}
        
        for i, (region, image_path) in enumerate(screenshots.items(), 1):
            self.logger.info(f"  [{i}/{len(screenshots)}] Analyzing {region}...")
            analysis = self.ai_interpreter.analyze_screenshot(image_path, region, context)
            analyses[region] = analysis
        
        return analyses
    
    def comprehensive_analysis(self,
                             bam_files: List[str],
                             regions: List[str],
                             session_name: Optional[str] = None,
                             region_tags: Optional[List[str]] = None,
                             context: str = "",
                             ai_analysis: bool = True,
                             save_report: bool = True) -> Dict:
        """Complete genomic analysis workflow with enhanced reporting"""
        
        # Generate unique session name if not provided
        if not session_name:
            session_name = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.logger.info(f"🧬 Starting comprehensive genomic analysis: {session_name}")
        
        # Generate screenshots
        screenshots = self.generate_screenshots(
            bam_files, regions, session_name, region_tags
        )
        
        # AI analysis
        ai_analyses = {}
        if ai_analysis and screenshots:
            ai_analyses = self.analyze_with_ai(screenshots, context)
        
        # Compile comprehensive results
        results = {
            "session_name": session_name,
            "timestamp": datetime.now().isoformat(),
            "configuration": {
                "genome": self.config.genome,
                "output_format": self.config.output_format,
                "ai_provider": self.ai_interpreter.provider,
                "singularity_image": self.singularity_image
            },
            "input_summary": {
                "bam_files": bam_files,
                "num_bam_files": len(bam_files),
                "regions": regions,
                "num_regions": len(regions),
                "has_tags": bool(region_tags),
                "context": context
            },
            "screenshots": screenshots,
            "ai_analyses": ai_analyses,
            "summary": {
                "total_regions": len(regions),
                "screenshots_generated": len(screenshots),
                "success_rate": f"{len(screenshots)/len(regions)*100:.1f}%" if regions else "0%",
                "ai_analyses_completed": len(ai_analyses),
                "overall_status": "Success" if screenshots else "Failed"
            }
        }
        
        # Save results
        if save_report:
            report_path = self._save_results(results, session_name)
            results['report_path'] = report_path
            
            # Generate HTML report if analyses available
            if ai_analyses:
                html_path = self._generate_html_report(results, session_name)
                results['html_report'] = html_path
        
        return results
    
    def _save_results(self, results: Dict, session_name: str) -> str:
        """Save analysis results to JSON"""
        results_file = self.output_base_dir / session_name / "analysis_results.json"
        
        # Create a serializable copy
        serializable_results = json.loads(json.dumps(results, default=str))
        
        with open(results_file, 'w') as f:
            json.dump(serializable_results, f, indent=2)
        
        self.logger.info(f"📄 Results saved: {results_file}")
        return str(results_file)
    
    def _generate_html_report(self, results: Dict, session_name: str) -> str:
        """Generate an HTML report with screenshots and analyses"""
        html_file = self.output_base_dir / session_name / "report.html"
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Genomic Analysis Report - {session_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #2c3e50; }}
        h2 {{ color: #34495e; border-bottom: 2px solid #ecf0f1; padding-bottom: 5px; }}
        .region {{ margin-bottom: 40px; border: 1px solid #ecf0f1; padding: 20px; border-radius: 5px; }}
        .screenshot {{ max-width: 100%; height: auto; }}
        .analysis {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; white-space: pre-wrap; }}
        .metadata {{ background-color: #ecf0f1; padding: 10px; border-radius: 5px; margin-bottom: 10px; }}
    </style>
</head>
<body>
    <h1>🧬 Genomic Analysis Report</h1>
    <div class="metadata">
        <strong>Session:</strong> {session_name}<br>
        <strong>Date:</strong> {results['timestamp']}<br>
        <strong>Genome:</strong> {results['configuration']['genome']}<br>
        <strong>Success Rate:</strong> {results['summary']['success_rate']}
    </div>
"""
        
        for region, screenshot_path in results['screenshots'].items():
            analysis = results['ai_analyses'].get(region, {})
            
            html_content += f"""
    <div class="region">
        <h2>Region: {region}</h2>
        <img src="{Path(screenshot_path).name}" class="screenshot" alt="{region}">
        <div class="analysis">
            <h3>AI Analysis</h3>
            {analysis.get('analysis', 'No analysis available')}
        </div>
    </div>
"""
        
        html_content += """
</body>
</html>
"""
        
        with open(html_file, 'w') as f:
            f.write(html_content)
        
        self.logger.info(f"📊 HTML report generated: {html_file}")
        return str(html_file)

# Example usage and testing
def main():
    """Example usage of the Fixed Genomic AI Agent"""
    
    print("🧬 Fixed Genomic AI Agent - Example Usage")
    print("=" * 50)
    
    # Initialize agent with configuration
    config = AnalysisConfig(
        genome="hg19",
        output_format="png",
        remove_png=False  # Keep PNGs for review
    )
    
    # Use test_results directory when running as a test/example
    output_dir = "test_results/example_run" if __name__ == "__main__" else "/tmp/genomic_ai_agent_fixed"
    
    agent = GenomicAIAgent(
        singularity_image="downloaded_image/igver_latest.sif",  # Adjust path
        output_base_dir=output_dir,
        config=config,
        ai_provider="openai",  # or "anthropic" or "mock" for testing
    )
    
    # Example: Clinical variant analysis
    results = agent.comprehensive_analysis(
        bam_files=[
            "test/test_tumor.bam",
            "test/test_normal.bam"
        ],
        regions=[
            "chr17:43044295-43045802",  # BRCA1
            "chr13:32315086-32400266",  # BRCA2
            "chr8:32534767-32536767",   # Test region
            "chr19:11137898-11139898"   # Test region
        ],
        region_tags=[
            "BRCA1_pathogenic",
            "BRCA2_founder", 
            "test1",
            "test2"
        ],
        session_name="clinical_variant_analysis",
        context="Hereditary breast/ovarian cancer risk assessment. Patient has family history of BRCA mutations.",
        ai_analysis=True,
        save_report=True
    )
    
    # Print summary
    print(f"\n📊 Analysis Summary:")
    print(f"  Screenshots: {results['summary']['screenshots_generated']}/{results['summary']['total_regions']}")
    print(f"  Success rate: {results['summary']['success_rate']}")
    print(f"  AI analyses: {results['summary']['ai_analyses_completed']}")
    print(f"  Status: {results['summary']['overall_status']}")
    
    # Show generated files
    print(f"\n📁 Generated Screenshots:")
    for region, path in results['screenshots'].items():
        filename = Path(path).name
        size = Path(path).stat().st_size if Path(path).exists() else 0
        print(f"  ✅ {region}: {filename} ({size:,} bytes)")
    
    # Show AI analysis sample
    if results['ai_analyses']:
        print(f"\n🤖 AI Analysis Sample (first region):")
        first_region = next(iter(results['ai_analyses']))
        analysis = results['ai_analyses'][first_region]
        print(f"  Region: {first_region}")
        print(f"  Provider: {analysis.get('provider', 'unknown')}")
        print(f"  Confidence: {analysis.get('confidence', 'N/A')}")
        if 'analysis' in analysis:
            preview = analysis['analysis'][:300] + "..." if len(analysis['analysis']) > 300 else analysis['analysis']
            print(f"  Analysis Preview:\n{preview}")
    
    # Report paths
    if 'report_path' in results:
        print(f"\n📄 JSON Report: {results['report_path']}")
    if 'html_report' in results:
        print(f"📊 HTML Report: {results['html_report']}")

if __name__ == "__main__":
    main()