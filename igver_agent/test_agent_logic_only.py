#!/usr/bin/env python3
"""
Test the fixed IGVer agent logic without actual Singularity execution
"""

import sys
import os
from pathlib import Path
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from igver_agent.main_igver_agent_fixed import (
    GenomicAIAgent, 
    AnalysisConfig,
    GenomicRegion,
    InputValidator,
    SmartSingularityMounter
)

def test_agent_components():
    """Test individual agent components"""
    
    print("=" * 60)
    print("🧬 Testing IGVer Agent Components")
    print("=" * 60)
    
    # Test 1: Parse tagged regions file
    print("\n1️⃣ Testing Region Parsing with Tags")
    print("-" * 40)
    
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
    
    print(f"✅ Parsed {len(regions)} regions from test_regions_tagged.txt:")
    for i, (region, tag) in enumerate(zip(regions, tags), 1):
        # Create GenomicRegion object
        chrom, coords = region.split(':')
        start, end = coords.split('-')
        gr = GenomicRegion(chrom, int(start), int(end), tag)
        print(f"  {i}. {gr} -> filename: {gr.to_filename_base()}.png")
    
    # Test 2: Input validation
    print("\n2️⃣ Testing Input Validation")
    print("-" * 40)
    
    validator = InputValidator()
    
    # Test BAM file validation
    test_bams = ["test/test_normal.bam", "test/test_tumor.bam"]
    print("Testing BAM validation:")
    for bam in test_bams:
        if Path(bam).exists():
            try:
                validated = validator.validate_bam_files([bam])
                print(f"  ✅ {bam} -> {validated[0]}")
            except Exception as e:
                print(f"  ❌ {bam}: {e}")
        else:
            print(f"  ⚠️  {bam} not found (expected for testing)")
    
    # Test Singularity check
    print("\nTesting Singularity check:")
    has_singularity = validator.check_singularity()
    print(f"  Singularity installed: {has_singularity}")
    
    # Test 3: Configuration
    print("\n3️⃣ Testing Configuration")
    print("-" * 40)
    
    config = AnalysisConfig(
        genome="hg19",
        output_format="png",
        max_panel_height=200,
        overlap_display="squish",
        remove_png=False
    )
    
    print("Configuration created:")
    for field, value in config.__dict__.items():
        print(f"  • {field}: {value}")
    
    # Test 4: Agent initialization (without Singularity)
    print("\n4️⃣ Testing Agent Initialization")
    print("-" * 40)
    
    # Set environment to skip Singularity
    os.environ['IGVER_NO_SINGULARITY'] = '1'
    
    try:
        agent = GenomicAIAgent(
            singularity_image=None,  # Skip Singularity
            output_base_dir="test_results/logic_test",
            config=config,
            ai_provider="mock"
        )
        print("✅ Agent initialized successfully")
        print(f"  Output dir: {agent.output_base_dir}")
        print(f"  AI provider: {agent.ai_interpreter.provider}")
        print(f"  Config genome: {agent.config.genome}")
    except Exception as e:
        print(f"❌ Agent initialization failed: {e}")
        return False
    
    # Test 5: Input file preparation
    print("\n5️⃣ Testing Input File Preparation")
    print("-" * 40)
    
    session_dir = agent.output_base_dir / "test_session"
    session_dir.mkdir(parents=True, exist_ok=True)
    
    # Create mock BAM files for testing
    mock_bams = []
    for bam in test_bams:
        mock_path = session_dir / Path(bam).name
        mock_path.touch()  # Create empty file
        mock_bams.append(str(mock_path))
    
    try:
        paths_input, regions_input, parsed_regions = agent.prepare_input_files(
            bam_files=mock_bams,
            regions=regions,
            region_tags=tags,
            session_dir=session_dir
        )
        
        print(f"✅ Input files prepared:")
        print(f"  Paths input: {paths_input}")
        print(f"  Regions input: {regions_input}")
        print(f"  Parsed regions: {len(parsed_regions)} regions")
        
        # Check if regions file was created
        if regions_input and regions_input[0].endswith('.txt'):
            regions_file = Path(regions_input[0])
            if regions_file.exists():
                print(f"\n  Created regions file: {regions_file}")
                print("  Contents:")
                with open(regions_file, 'r') as f:
                    for line in f.readlines()[:5]:  # Show first 5 lines
                        print(f"    {line.rstrip()}")
    except Exception as e:
        print(f"❌ Input preparation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 6: Mock AI analysis
    print("\n6️⃣ Testing Mock AI Analysis")
    print("-" * 40)
    
    mock_screenshot = session_dir / "mock_screenshot.png"
    mock_screenshot.touch()  # Create empty file
    
    try:
        analysis = agent.ai_interpreter.analyze_screenshot(
            str(mock_screenshot),
            "chr1:1000-2000",
            context="Test analysis"
        )
        
        print("✅ Mock AI analysis completed:")
        print(f"  Provider: {analysis.get('provider')}")
        print(f"  Region: {analysis.get('region')}")
        print(f"  Confidence: {analysis.get('confidence')}")
        print(f"  Has analysis: {'analysis' in analysis}")
        
    except Exception as e:
        print(f"❌ Mock AI analysis failed: {e}")
        return False
    
    # Test 7: Report generation logic
    print("\n7️⃣ Testing Report Generation Logic")
    print("-" * 40)
    
    mock_results = {
        "session_name": "test_session",
        "timestamp": "2024-01-01T12:00:00",
        "configuration": {
            "genome": config.genome,
            "output_format": config.output_format
        },
        "input_summary": {
            "bam_files": mock_bams,
            "num_bam_files": len(mock_bams),
            "regions": regions,
            "num_regions": len(regions)
        },
        "screenshots": {
            regions[0]: str(mock_screenshot)
        },
        "ai_analyses": {
            regions[0]: analysis
        },
        "summary": {
            "total_regions": len(regions),
            "screenshots_generated": 1,
            "success_rate": f"{1/len(regions)*100:.1f}%",
            "overall_status": "Partial"
        }
    }
    
    try:
        # Save JSON report
        json_path = agent._save_results(mock_results, "test_session")
        print(f"✅ JSON report saved: {json_path}")
        
        # Generate HTML report
        html_path = agent._generate_html_report(mock_results, "test_session")
        print(f"✅ HTML report generated: {html_path}")
        
    except Exception as e:
        print(f"❌ Report generation failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ ALL COMPONENT TESTS PASSED!")
    print("=" * 60)
    
    # Clean up environment
    del os.environ['IGVER_NO_SINGULARITY']
    
    return True

if __name__ == "__main__":
    success = test_agent_components()
    sys.exit(0 if success else 1)