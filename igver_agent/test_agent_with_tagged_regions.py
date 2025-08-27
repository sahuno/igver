#!/usr/bin/env python3
"""
Test the fixed IGVer agent with multi-region tagged file
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import igver
sys.path.insert(0, str(Path(__file__).parent.parent))

from igver_agent.main_igver_agent_fixed import GenomicAIAgent, AnalysisConfig

def test_with_tagged_regions():
    """Test the agent with the tagged regions file"""
    
    print("=" * 60)
    print("🧬 Testing Fixed IGVer Agent with Tagged Regions")
    print("=" * 60)
    
    # Parse the tagged regions file
    regions = []
    tags = []
    
    with open('test_regions_tagged.txt', 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                parts = line.split()
                if len(parts) >= 2:
                    regions.append(parts[0])
                    tags.append(parts[1] if len(parts) > 1 else None)
    
    print(f"\n📍 Found {len(regions)} regions with tags:")
    for i, (region, tag) in enumerate(zip(regions, tags), 1):
        print(f"  {i}. {region} [{tag}]")
    
    # Configure the agent
    config = AnalysisConfig(
        genome="hg19",  # Using hg19 as per test files
        output_format="png",
        remove_png=False,  # Keep PNGs for inspection
        max_panel_height=200,
        overlap_display="squish"
    )
    
    # Check for Singularity image
    singularity_images = [
        "downloaded_image/igver_latest.sif",
        "/tmp/igver_latest.sif",
        "igver_latest.sif"
    ]
    
    singularity_image = None
    for img in singularity_images:
        if Path(img).exists():
            singularity_image = img
            print(f"\n✅ Found Singularity image: {img}")
            break
    
    if not singularity_image:
        # Try docker image
        singularity_image = "docker://sahuno/igver:latest"
        print(f"\n📦 Using Docker image: {singularity_image}")
    
    # Initialize the agent
    print("\n🚀 Initializing GenomicAIAgent...")
    agent = GenomicAIAgent(
        singularity_image=singularity_image,
        output_base_dir="test_results/tagged_regions_test",
        config=config,
        ai_provider="mock"  # Use mock for testing without API keys
    )
    
    # Test BAM files
    test_bams = [
        "test/test_normal.bam",
        "test/test_tumor.bam"
    ]
    
    # Verify BAM files exist
    print("\n📂 Checking BAM files:")
    valid_bams = []
    for bam in test_bams:
        if Path(bam).exists():
            print(f"  ✅ Found: {bam}")
            valid_bams.append(bam)
        else:
            print(f"  ❌ Missing: {bam}")
    
    if not valid_bams:
        print("\n⚠️  No BAM files found. Creating mock BAM for testing...")
        # For testing, we'll proceed anyway to test the agent logic
        valid_bams = ["test/test_normal.bam"]  # Will fail but test error handling
    
    # Run comprehensive analysis
    print("\n🔬 Starting comprehensive analysis...")
    print("-" * 40)
    
    try:
        results = agent.comprehensive_analysis(
            bam_files=valid_bams,
            regions=regions,
            region_tags=tags,
            session_name="tagged_regions_test",
            context="Testing IGVer agent with tagged multi-region file",
            ai_analysis=True,  # Will use mock AI
            save_report=True
        )
        
        # Display results
        print("\n" + "=" * 60)
        print("📊 ANALYSIS RESULTS")
        print("=" * 60)
        
        print(f"\n📈 Summary:")
        print(f"  • Total regions: {results['summary']['total_regions']}")
        print(f"  • Screenshots generated: {results['summary']['screenshots_generated']}")
        print(f"  • Success rate: {results['summary']['success_rate']}")
        print(f"  • AI analyses: {results['summary']['ai_analyses_completed']}")
        print(f"  • Overall status: {results['summary']['overall_status']}")
        
        if results['screenshots']:
            print(f"\n📸 Generated Screenshots:")
            for region, path in results['screenshots'].items():
                fname = Path(path).name if path else "N/A"
                print(f"  • {region}: {fname}")
        else:
            print(f"\n⚠️  No screenshots were generated")
        
        if results['ai_analyses']:
            print(f"\n🤖 AI Analysis Results (Mock):")
            for region, analysis in list(results['ai_analyses'].items())[:2]:  # Show first 2
                print(f"\n  Region: {region}")
                print(f"  Provider: {analysis.get('provider', 'unknown')}")
                print(f"  Confidence: {analysis.get('confidence', 'N/A')}")
                if 'analysis' in analysis:
                    preview = analysis['analysis'][:200] + "..."
                    print(f"  Preview: {preview}")
        
        # Show file paths
        if 'report_path' in results:
            print(f"\n📄 JSON report saved: {results['report_path']}")
        if 'html_report' in results:
            print(f"📊 HTML report saved: {results['html_report']}")
        
        print("\n✅ Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        print("\nTraceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Run the test
    success = test_with_tagged_regions()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)