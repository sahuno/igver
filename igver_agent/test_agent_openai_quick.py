#!/usr/bin/env python3
"""
Quick test of IGVer agent with OpenAI integration and tagged regions
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from igver_agent.main_igver_agent_fixed import GenomicAIAgent, AnalysisConfig

def quick_openai_test():
    """Quick test with real OpenAI API"""
    
    print("=" * 60)
    print("🧬 Testing IGVer Agent with OpenAI GPT-4V")
    print("=" * 60)
    
    # Check for OpenAI key
    if not os.environ.get('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY not found in environment")
        return False
    
    print("✅ OpenAI API key found in environment")
    
    # Parse the tagged regions file
    regions = []
    tags = []
    
    with open('../test_regions_tagged.txt', 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                parts = line.split()
                if len(parts) >= 2:
                    regions.append(parts[0])
                    tags.append(parts[1])
    
    # Use only first 2 regions for quick test
    regions = regions[:2]
    tags = tags[:2]
    
    print(f"\n📍 Testing with {len(regions)} regions:")
    for i, (region, tag) in enumerate(zip(regions, tags), 1):
        print(f"  {i}. {region} [{tag}]")
    
    # Configure agent
    config = AnalysisConfig(
        genome="hg19",
        output_format="png",
        remove_png=False
    )
    
    # Initialize agent with OpenAI
    print("\n🚀 Initializing agent with OpenAI provider...")
    
    # Try to use existing singularity image or docker
    singularity_image = None
    for path in ["../downloaded_image/igver_latest.sif", "docker://sahuno/igver:latest"]:
        if Path(path).exists() or path.startswith("docker://"):
            singularity_image = path
            break
    
    agent = GenomicAIAgent(
        singularity_image=singularity_image,
        output_base_dir="test_results/openai_test",
        config=config,
        ai_provider="openai"  # Use real OpenAI
    )
    
    # Test BAM files
    test_bams = [
        "../test/test_normal.bam",
        "../test/test_tumor.bam"
    ]
    
    # Check if BAMs exist
    valid_bams = []
    for bam in test_bams:
        if Path(bam).exists():
            valid_bams.append(bam)
            print(f"  ✅ Found BAM: {Path(bam).name}")
    
    if not valid_bams:
        print("\n⚠️  No BAM files found - will test AI only")
        # Create mock screenshot for AI test
        mock_dir = Path("test_results/openai_test/mock")
        mock_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a simple test image
        from PIL import Image, ImageDraw, ImageFont
        import matplotlib.pyplot as plt
        
        # Create a mock IGV-like screenshot
        img = Image.new('RGB', (800, 400), color='white')
        draw = ImageDraw.Draw(img)
        
        # Draw some mock genomic features
        draw.rectangle([50, 100, 750, 150], fill='lightblue', outline='blue')
        draw.text((60, 110), f"Region: {regions[0]}", fill='black')
        draw.rectangle([100, 200, 700, 250], fill='lightgreen', outline='green')
        draw.text((110, 210), "Mock Coverage Track", fill='black')
        
        mock_path = mock_dir / "mock_igv_screenshot.png"
        img.save(mock_path)
        
        print(f"  ✅ Created mock screenshot: {mock_path}")
        
        # Test AI analysis directly
        print("\n🤖 Testing OpenAI GPT-4V analysis...")
        analysis = agent.ai_interpreter.analyze_screenshot(
            str(mock_path),
            regions[0],
            context="Test genomic region with potential variants"
        )
        
        print("\n📊 AI Analysis Result:")
        print(f"  Provider: {analysis.get('provider', 'unknown')}")
        print(f"  Model: {analysis.get('model', 'unknown')}")
        print(f"  Region: {analysis.get('region', 'unknown')}")
        print(f"  Confidence: {analysis.get('confidence', 'N/A')}")
        
        if 'error' in analysis:
            print(f"  ❌ Error: {analysis['error']}")
        elif 'analysis' in analysis:
            # Show first 500 chars of analysis
            text = analysis['analysis']
            preview = text[:500] + "..." if len(text) > 500 else text
            print(f"\n  Analysis Preview:\n{'-'*40}")
            print(preview)
            print('-'*40)
        
        return 'error' not in analysis
    
    else:
        # Run full analysis with real BAMs
        print("\n🔬 Running analysis with real BAM files...")
        try:
            results = agent.comprehensive_analysis(
                bam_files=valid_bams,
                regions=regions,
                region_tags=tags,
                session_name="openai_test",
                context="Testing OpenAI GPT-4V integration with genomic data",
                ai_analysis=True,
                save_report=True
            )
            
            print(f"\n📊 Results:")
            print(f"  Screenshots: {results['summary']['screenshots_generated']}/{len(regions)}")
            print(f"  AI analyses: {results['summary']['ai_analyses_completed']}")
            
            if results['ai_analyses']:
                first_region = next(iter(results['ai_analyses']))
                analysis = results['ai_analyses'][first_region]
                print(f"\n🤖 Sample AI Analysis for {first_region}:")
                print(f"  Provider: {analysis.get('provider')}")
                print(f"  Model: {analysis.get('model')}")
                text = analysis.get('analysis', '')[:300] + "..."
                print(f"  Preview: {text}")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    # Activate virtual environment's packages
    venv_site_packages = Path("venv/lib/python3.10/site-packages")
    if venv_site_packages.exists():
        sys.path.insert(0, str(venv_site_packages))
    
    success = quick_openai_test()
    print("\n" + "=" * 60)
    if success:
        print("✅ OpenAI integration test completed!")
    else:
        print("❌ OpenAI integration test failed")
    print("=" * 60)