#!/usr/bin/env python3
"""
🧬 FINAL Genomic AI Agent - Complete Implementation
Combines IGV screenshot generation with AI-powered genomic interpretation

Key Features:
- Smart Singularity mounting (including image parent directory)
- Flexible input handling (multi-line BAM files, tagged regions)
- AI-powered screenshot interpretation (OpenAI/Anthropic)
- Comprehensive error handling and validation
- Production-ready logging and reporting
"""

import igver
import os
import sys
import json
import logging
import base64
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass
import requests

# AI Integration imports (install with: pip install openai anthropic)
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

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
    
    def __str__(self):
        return f"{self.chromosome}:{self.start}-{self.end}"
    
    def to_filename_base(self):
        """Generate filename-safe string representation"""
        base = f"{self.chromosome}-{self.start}-{self.end}"
        return f"{base}.{self.tag}" if self.tag else base

class SmartSingularityMounter:
    """Handles intelligent Singularity mounting"""
    
    def __init__(self, singularity_image_path: str):
        self.image_path = Path(singularity_image_path).resolve()
        self.logger = logging.getLogger(__name__)
    
    def get_mount_args(self, bam_files: List[str], output_dir: str, 
                       additional_paths: Optional[List[str]] = None) -> str:
        """Generate optimal mount points for Singularity"""
        mount_points = set()
        
        # Always mount common directories
        mount_points.update(['/home', '/tmp'])
        
        # 🔑 KEY INSIGHT: Mount singularity image parent directory
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
            openai.api_key = self.api_key
        elif provider == "anthropic" and ANTHROPIC_AVAILABLE:
            self.client = anthropic.Anthropic(api_key=self.api_key)
    
    def analyze_screenshot(self, image_path: str, region: str, context: str = "") -> Dict:
        """Analyze genomic screenshot using AI vision models"""
        
        if not os.path.exists(image_path):
            return {"error": f"Image not found: {image_path}"}
        
        prompt = f"""
        Analyze this IGV genomic visualization screenshot for region {region}.
        
        As a genomic data analyst, provide:
        1. **Coverage Assessment**: Depth, uniformity, gaps
        2. **Read Alignment Quality**: Misalignments, soft clipping issues
        3. **Variant Detection**: Visible SNPs, indels, structural variants
        4. **Quality Control**: Artifacts, PCR duplicates, mapping issues
        5. **Clinical Relevance**: Pathogenic potential of variants (if applicable)
        6. **Recommendations**: Validation steps, follow-up analysis
        
        Context: {context}
        
        Be specific about genomic coordinates and provide confidence levels.
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
        """OpenAI GPT-4V analysis"""
        base64_image = self._encode_image_base64(image_path)
        
        response = openai.chat.completions.create(
            model="gpt-4-vision-preview",
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
            max_tokens=1500
        )
        
        return {
            "provider": "openai",
            "model": "gpt-4-vision-preview",
            "region": region,
            "analysis": response.choices[0].message.content,
            "confidence": 0.85
        }
    
    def _analyze_with_anthropic(self, image_path: str, prompt: str, region: str) -> Dict:
        """Anthropic Claude analysis"""
        base64_image = self._encode_image_base64(image_path)
        
        response = self.client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1500,
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
            "confidence": 0.88
        }
    
    def _mock_analysis(self, region: str) -> Dict:
        """Mock analysis when AI providers unavailable"""
        return {
            "provider": "mock",
            "region": region,
            "analysis": f"Mock AI analysis for {region}. Install openai/anthropic packages for real AI analysis.",
            "confidence": 0.5
        }

class GenomicAIAgent:
    """🧬 FINAL Genomic AI Agent - Complete Implementation"""
    
    def __init__(self, 
                 singularity_image: str,
                 output_base_dir: str = "/tmp/genomic_ai_agent",
                 genome: str = "hg38",
                 ai_provider: str = "openai",
                 ai_api_key: Optional[str] = None):
        
        self.singularity_image = singularity_image
        self.output_base_dir = Path(output_base_dir)
        self.genome = genome
        
        # Initialize components
        if singularity_image:
            self.mounter = SmartSingularityMounter(singularity_image)
        else:
            self.mounter = None
        
        self.ai_interpreter = AIGenomicInterpreter(ai_provider, ai_api_key)
        
        # Setup
        self.output_base_dir.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
        self.logger = logging.getLogger(__name__)
    
    def create_input_files(self, bam_files: List[str], regions: List[str], 
                          region_tags: Optional[List[str]], session_dir: Path) -> Tuple[List[str], List[str], List[GenomicRegion]]:
        """Create input files for igver when beneficial"""
        
        # Create BAM list file for multi-BAM scenarios
        if len(bam_files) > 2:
            bam_list_file = session_dir / "bam_list.txt"
            with open(bam_list_file, 'w') as f:
                f.write("# BAM files for IGV analysis\n")
                for bam in bam_files:
                    f.write(f"{Path(bam).expanduser().resolve()}\n")
            paths_input = [str(bam_list_file)]
            self.logger.info(f"Created BAM list file with {len(bam_files)} files")
        else:
            paths_input = bam_files
        
        # Create regions file when tags are present or many regions
        parsed_regions = []
        if region_tags or len(regions) > 5:
            regions_file = session_dir / "regions_list.txt"
            with open(regions_file, 'w') as f:
                f.write("# Genomic regions with optional tags\n")
                f.write("# Format: chr:start-end [tag]\n")
                for i, region in enumerate(regions):
                    tag = region_tags[i] if region_tags and i < len(region_tags) else None
                    parsed_region = self._parse_region(region, tag)
                    parsed_regions.append(parsed_region)
                    
                    if tag:
                        f.write(f"{region}\t{tag}\n")
                    else:
                        f.write(f"{region}\n")
            regions_input = [str(regions_file)]
            self.logger.info(f"Created regions file with {len(regions)} regions")
        else:
            regions_input = regions
            parsed_regions = [self._parse_region(r) for r in regions]
        
        return paths_input, regions_input, parsed_regions
    
    def _parse_region(self, region_str: str, tag: Optional[str] = None) -> GenomicRegion:
        """Parse genomic region string"""
        chrom, coords = region_str.split(':')
        start, end = coords.split('-')
        return GenomicRegion(chrom, int(start), int(end), tag)
    
    def generate_screenshots(self, 
                           bam_files: List[str],
                           regions: List[str],
                           session_name: str = "analysis",
                           region_tags: Optional[List[str]] = None,
                           additional_mount_paths: Optional[List[str]] = None) -> Dict[str, str]:
        """Generate IGV screenshots with smart input handling"""
        
        session_dir = self.output_base_dir / session_name
        session_dir.mkdir(exist_ok=True)
        
        self.logger.info(f"🔬 Generating screenshots: {len(regions)} regions, {len(bam_files)} BAM files")
        
        try:
            # Prepare inputs
            paths_input, regions_input, parsed_regions = self.create_input_files(
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
            
            # Generate screenshots
            self.logger.info("Calling igver.load_screenshots...")
            figures = igver.load_screenshots(
                paths=paths_input,
                regions=regions_input,
                output_dir=str(session_dir),
                genome=self.genome,
                singularity_image=self.singularity_image,
                singularity_args=singularity_args,
                overwrite=True,
                remove_png=False
            )
            
            # Discover generated files
            screenshots = self._discover_screenshots(parsed_regions, session_dir)
            
            success_count = len(screenshots)
            self.logger.info(f"✅ Generated {success_count}/{len(regions)} screenshots")
            
            return screenshots
            
        except Exception as e:
            self.logger.error(f"Screenshot generation failed: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {}
    
    def _discover_screenshots(self, parsed_regions: List[GenomicRegion], session_dir: Path) -> Dict[str, str]:
        """Discover generated PNG files"""
        screenshots = {}
        png_files = list(session_dir.glob("*.png"))
        
        for region in parsed_regions:
            region_str = str(region)
            
            # Try exact filename prediction
            predicted_name = f"{region.to_filename_base()}.png"
            predicted_path = session_dir / predicted_name
            
            if predicted_path.exists() and predicted_path.stat().st_size > 0:
                screenshots[region_str] = str(predicted_path)
                size = predicted_path.stat().st_size
                self.logger.info(f"  ✅ {region_str} -> {predicted_name} ({size:,} bytes)")
            else:
                # Try pattern matching
                base_pattern = f"{region.chromosome}-{region.start}-{region.end}"
                matches = [f for f in png_files if base_pattern in f.name]
                
                if matches:
                    best_match = matches[0]
                    screenshots[region_str] = str(best_match)
                    size = best_match.stat().st_size
                    self.logger.info(f"  ✅ {region_str} -> {best_match.name} ({size:,} bytes)")
                else:
                    self.logger.warning(f"  ❌ {region_str} -> No screenshot found")
        
        return screenshots
    
    def analyze_with_ai(self, screenshots: Dict[str, str], context: str = "") -> Dict[str, Dict]:
        """Run AI analysis on screenshots"""
        if not screenshots:
            return {}
        
        self.logger.info(f"🤖 Running AI analysis on {len(screenshots)} screenshots...")
        analyses = {}
        
        for region, image_path in screenshots.items():
            self.logger.info(f"  Analyzing {region}...")
            analysis = self.ai_interpreter.analyze_screenshot(image_path, region, context)
            analyses[region] = analysis
        
        return analyses
    
    def comprehensive_analysis(self,
                             bam_files: List[str],
                             regions: List[str],
                             session_name: str = "analysis",
                             region_tags: Optional[List[str]] = None,
                             context: str = "",
                             ai_analysis: bool = True) -> Dict:
        """🧬 Complete genomic analysis workflow"""
        
        self.logger.info(f"🧬 Starting comprehensive genomic analysis: {session_name}")
        
        # Generate screenshots
        screenshots = self.generate_screenshots(
            bam_files, regions, session_name, region_tags
        )
        
        # AI analysis
        ai_analyses = {}
        if ai_analysis and screenshots:
            ai_analyses = self.analyze_with_ai(screenshots, context)
        
        # Compile results
        results = {
            "session_name": session_name,
            "timestamp": self._get_timestamp(),
            "input_summary": {
                "bam_files": len(bam_files),
                "regions": len(regions),
                "has_tags": bool(region_tags),
                "context": context
            },
            "screenshots": screenshots,
            "ai_analyses": ai_analyses,
            "summary": {
                "total_regions": len(regions),
                "screenshots_generated": len(screenshots),
                "success_rate": f"{len(screenshots)/len(regions)*100:.1f}%",
                "ai_analyses_completed": len(ai_analyses),
                "overall_status": "Success" if screenshots else "Failed"
            }
        }
        
        # Save results
        self._save_results(results, session_name)
        
        return results
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _save_results(self, results: Dict, session_name: str) -> str:
        """Save analysis results to JSON"""
        results_file = self.output_base_dir / session_name / "analysis_results.json"
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        self.logger.info(f"📄 Results saved: {results_file}")
        return str(results_file)

# 🎯 MAIN EXAMPLE USAGE
def main():
    """Example usage of the Final Genomic AI Agent"""
    
    print("🧬 Genomic AI Agent - Example Usage")
    print("=" * 50)
    
    # Initialize agent
    agent = GenomicAIAgent(
        singularity_image="downloaded_image/igver_latest.sif",  # Adjust path
        output_base_dir="/tmp/genomic_ai_agent",
        genome="hg19",  # Match your test
        ai_provider="openai",  # or "anthropic" or "mock"
    )
    
    # Clinical analysis example
    results = agent.comprehensive_analysis(
        bam_files=[
            "test/test_tumor.bam",
            "test/test_normal.bam"
        ],
        regions=[
            "chr17:43044295-43045802",  # BRCA1
            "chr13:32315086-32400266",  # BRCA2  
            "chr8:32534767-32536767",   # Test region 1
            "chr19:11137898-11139898"   # Test region 2
        ],
        region_tags=[
            "BRCA1_pathogenic_region",
            "BRCA2_founder_mutations", 
            "test_region_1",
            "test_region_2"
        ],
        session_name="clinical_variant_screening",
        context="Hereditary breast cancer risk assessment",
        ai_analysis=True
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
        print(f"  ✅ {region}: {filename}")
    
    if results['ai_analyses']:
        print(f"\n🤖 AI Analysis Sample (first region):")
        first_region = next(iter(results['ai_analyses']))
        analysis = results['ai_analyses'][first_region]
        print(f"  Region: {analysis['region']}")
        print(f"  Provider: {analysis.get('provider', 'unknown')}")
        print(f"  Confidence: {analysis.get('confidence', 'N/A')}")
        if 'analysis' in analysis:
            preview = analysis['analysis'][:200] + "..." if len(analysis['analysis']) > 200 else analysis['analysis']
            print(f"  Analysis: {preview}")

if __name__ == "__main__":
    main()
