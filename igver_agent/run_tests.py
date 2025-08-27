#!/usr/bin/env python3
"""
Test runner for IGVer Agent
Runs various tests and generates a summary report
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from test_config import (
    get_test_output_dir,
    get_singularity_image,
    get_valid_bam_files,
    summarize_test_results,
    QUICK_TEST_REGIONS,
    TEST_REGION_FILES
)

from main_igver_agent_fixed import GenomicAIAgent, AnalysisConfig

def run_test_suite(test_type: str = "all"):
    """Run comprehensive test suite"""
    
    print("=" * 60)
    print("🧬 IGVer Agent Test Suite")
    print("=" * 60)
    print(f"Test type: {test_type}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    results = {}
    
    # Test 1: Logic test (no Singularity)
    if test_type in ["all", "logic"]:
        print("\n1️⃣ Running logic test...")
        results['logic'] = run_logic_test()
    
    # Test 2: Mock AI test
    if test_type in ["all", "mock"]:
        print("\n2️⃣ Running mock AI test...")
        results['mock'] = run_mock_ai_test()
    
    # Test 3: Tagged regions test
    if test_type in ["all", "tagged"]:
        print("\n3️⃣ Running tagged regions test...")
        results['tagged'] = run_tagged_test()
    
    # Test 4: OpenAI test (if API key available)
    if test_type in ["all", "openai"]:
        if os.environ.get('OPENAI_API_KEY'):
            print("\n4️⃣ Running OpenAI test...")
            results['openai'] = run_openai_test()
        else:
            print("\n4️⃣ Skipping OpenAI test (no API key)")
    
    # Generate summary report
    generate_test_report(results)
    
    # Show results summary
    summarize_test_results()
    
    return results

def run_logic_test():
    """Test without Singularity"""
    try:
        os.environ['IGVER_NO_SINGULARITY'] = '1'
        
        config = AnalysisConfig(genome="hg19")
        agent = GenomicAIAgent(
            singularity_image=None,
            output_base_dir=str(get_test_output_dir('logic')),
            config=config,
            ai_provider="mock"
        )
        
        # Create mock files
        test_dir = get_test_output_dir('logic') / 'test_session'
        test_dir.mkdir(exist_ok=True)
        
        mock_bam = test_dir / 'test.bam'
        mock_bam.touch()
        
        _, _, parsed_regions = agent.prepare_input_files(
            bam_files=[str(mock_bam)],
            regions=QUICK_TEST_REGIONS,
            region_tags=["test1", "test2"],
            session_dir=test_dir
        )
        
        del os.environ['IGVER_NO_SINGULARITY']
        
        print("  ✅ Logic test passed")
        return {'status': 'passed', 'regions_parsed': len(parsed_regions)}
        
    except Exception as e:
        print(f"  ❌ Logic test failed: {e}")
        return {'status': 'failed', 'error': str(e)}

def run_mock_ai_test():
    """Test with mock AI provider"""
    try:
        config = AnalysisConfig(genome="hg19", remove_png=False)
        
        agent = GenomicAIAgent(
            singularity_image=get_singularity_image(),
            output_base_dir=str(get_test_output_dir('mock')),
            config=config,
            ai_provider="mock"
        )
        
        # Create mock screenshot
        mock_dir = get_test_output_dir('mock') / 'screenshots'
        mock_dir.mkdir(exist_ok=True)
        mock_png = mock_dir / 'test.png'
        
        # Create simple image
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='white')
        img.save(mock_png)
        
        # Test AI analysis
        result = agent.ai_interpreter.analyze_screenshot(
            str(mock_png),
            "chr1:1000-2000",
            context="Test"
        )
        
        if 'error' not in result:
            print("  ✅ Mock AI test passed")
            return {'status': 'passed', 'provider': result.get('provider')}
        else:
            raise Exception(result['error'])
            
    except Exception as e:
        print(f"  ❌ Mock AI test failed: {e}")
        return {'status': 'failed', 'error': str(e)}

def run_tagged_test():
    """Test with tagged regions file"""
    try:
        # Parse tagged regions file
        tagged_file = TEST_REGION_FILES.get('tagged')
        if not tagged_file or not tagged_file.exists():
            raise FileNotFoundError("Tagged regions file not found")
        
        regions = []
        tags = []
        with open(tagged_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split()
                    regions.append(parts[0])
                    tags.append(parts[1] if len(parts) > 1 else None)
        
        # Use only first 2 regions for quick test
        regions = regions[:2]
        tags = tags[:2]
        
        config = AnalysisConfig(genome="hg19")
        agent = GenomicAIAgent(
            singularity_image=get_singularity_image(),
            output_base_dir=str(get_test_output_dir('tagged')),
            config=config,
            ai_provider="mock"
        )
        
        bam_files = get_valid_bam_files()
        if not bam_files:
            # Create mock BAMs
            test_dir = get_test_output_dir('tagged')
            mock_bam = test_dir / 'test.bam'
            mock_bam.touch()
            bam_files = [str(mock_bam)]
        
        results = agent.comprehensive_analysis(
            bam_files=bam_files[:1],  # Use only one BAM for speed
            regions=regions,
            region_tags=tags,
            session_name=f"tagged_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            context="Tagged regions test",
            ai_analysis=False  # Skip AI for speed
        )
        
        success_rate = results['summary'].get('success_rate', '0%')
        print(f"  ✅ Tagged test passed (success rate: {success_rate})")
        return {
            'status': 'passed',
            'regions': len(regions),
            'screenshots': results['summary']['screenshots_generated'],
            'success_rate': success_rate
        }
        
    except Exception as e:
        print(f"  ❌ Tagged test failed: {e}")
        return {'status': 'failed', 'error': str(e)}

def run_openai_test():
    """Test with real OpenAI API"""
    try:
        from main_igver_agent_fixed import AIGenomicInterpreter
        
        # Test API connection first
        interpreter = AIGenomicInterpreter('openai')
        
        # Create test image
        test_dir = get_test_output_dir('openai')
        test_img = test_dir / 'test_api.png'
        
        from PIL import Image, ImageDraw
        img = Image.new('RGB', (400, 200), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "IGV Test Screenshot", fill='black')
        draw.rectangle([50, 50, 350, 150], outline='blue', width=2)
        img.save(test_img)
        
        # Test analysis
        result = interpreter.analyze_screenshot(
            str(test_img),
            "chr1:1000-2000",
            context="API connection test"
        )
        
        if 'error' not in result:
            print(f"  ✅ OpenAI test passed (model: {result.get('model')})")
            return {
                'status': 'passed',
                'model': result.get('model'),
                'provider': result.get('provider')
            }
        else:
            raise Exception(result['error'])
            
    except Exception as e:
        print(f"  ❌ OpenAI test failed: {e}")
        return {'status': 'failed', 'error': str(e)}

def generate_test_report(results):
    """Generate test report"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'tests_run': len(results),
        'tests_passed': sum(1 for r in results.values() if r.get('status') == 'passed'),
        'tests_failed': sum(1 for r in results.values() if r.get('status') == 'failed'),
        'details': results
    }
    
    # Save report
    report_file = get_test_output_dir('reports') / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_file.parent.mkdir(exist_ok=True)
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Test report saved: {report_file}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Tests run: {report['tests_run']}")
    print(f"✅ Passed: {report['tests_passed']}")
    print(f"❌ Failed: {report['tests_failed']}")
    
    if report['tests_failed'] > 0:
        print("\nFailed tests:")
        for name, result in results.items():
            if result.get('status') == 'failed':
                print(f"  • {name}: {result.get('error', 'Unknown error')}")
    
    return report

def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run IGVer Agent tests')
    parser.add_argument('--test', choices=['all', 'logic', 'mock', 'tagged', 'openai'],
                       default='all', help='Test to run')
    parser.add_argument('--cleanup', action='store_true',
                       help='Clean up old test results')
    parser.add_argument('--summary', action='store_true',
                       help='Show summary only')
    
    args = parser.parse_args()
    
    if args.summary:
        summarize_test_results()
        return
    
    if args.cleanup:
        from test_config import cleanup_old_results
        cleanup_old_results(keep_latest=3)
        print("✅ Cleanup complete")
        return
    
    # Run tests
    results = run_test_suite(args.test)
    
    # Exit code based on results
    failed = sum(1 for r in results.values() if r.get('status') == 'failed')
    sys.exit(failed)

if __name__ == "__main__":
    main()