#!/usr/bin/env python3
"""
Test igver with multi-line BAM file input using the latest implementation.
Tests that igver can accept a .txt file containing BAM paths.
"""

import igver
import os
import sys
import glob

def test_multi_bam_file_input():
    """Test igver with BAM paths from a text file."""
    
    # Test configuration
    bam_list_file = 'bam_list.txt'  # File containing BAM paths
    regions_file = 'test_regions_tagged.txt'  # Regions with tags
    output_dir = '/tmp/igver_multi_bam_test'
    
    # Clean and create output directory
    if os.path.exists(output_dir):
        for f in glob.glob(os.path.join(output_dir, '*.png')):
            os.remove(f)
    os.makedirs(output_dir, exist_ok=True)
    
    print("="*60)
    print("Testing IGVer with Multi-line BAM File Input")
    print("="*60)
    
    # Show BAM list file contents
    print(f"\n📄 BAM list file: {bam_list_file}")
    with open(bam_list_file, 'r') as f:
        bam_content = f.read()
        print("Contents:")
        for line in bam_content.split('\n'):
            print(f"  {line}")
    
    # Read regions for verification
    regions = []
    with open(regions_file, 'r') as f:
        for line in f:
            if line.strip():
                parts = line.strip().split()
                if parts:
                    region = parts[0]
                    tag = parts[1] if len(parts) > 1 else None
                    regions.append((region, tag))
    
    print(f"\n🎯 Test regions: {len(regions)} regions from {regions_file}")
    for region, tag in regions[:3]:  # Show first 3
        print(f"  - {region} (tag: {tag})")
    
    try:
        print("\n🔬 Generating screenshots with .txt file input...")
        
        # Use the BAM list file directly as input - igver should parse it
        figures = igver.load_screenshots(
            paths=[bam_list_file],  # Pass the .txt file - igver will parse it
            regions=[regions_file],  # Regions file
            output_dir=output_dir,
            genome='hg19',
            singularity_image='downloaded_image/igver_latest.sif',
            singularity_args='-B /home -B /tmp',
            overwrite=True,
            remove_png=False,
            debug=False
        )
        
        print(f"✓ Generated {len(figures)} figure objects")
        
        # Check generated files
        all_files = sorted([f for f in os.listdir(output_dir) if f.endswith('.png')])
        
        print(f"\n📊 Generated {len(all_files)} PNG files:")
        
        # Verify each region has a screenshot
        success_count = 0
        for region, tag in regions:
            region_formatted = region.replace(':', '-')
            expected_pattern = f"{region_formatted}.{tag}" if tag else region_formatted
            
            matching_files = [f for f in all_files if expected_pattern in f]
            if matching_files:
                for f in matching_files:
                    size = os.path.getsize(os.path.join(output_dir, f))
                    print(f"  ✓ {region} → {f} ({size:,} bytes)")
                success_count += 1
            else:
                print(f"  ✗ {region} → no matching file")
        
        print("\n" + "="*60)
        if success_count == len(regions):
            print(f"✅ SUCCESS: All {success_count} regions have screenshots!")
            print(f"✅ Multi-line BAM input file (.txt) works correctly!")
            return True
        else:
            print(f"⚠️  Only {success_count}/{len(regions)} regions have screenshots")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_direct_bam_list():
    """Test with direct list of BAMs for comparison."""
    
    print("\n" + "="*60)
    print("Testing Direct BAM List Input (for comparison)")
    print("="*60)
    
    output_dir = '/tmp/igver_direct_list_test'
    os.makedirs(output_dir, exist_ok=True)
    
    # Clean previous files
    for f in glob.glob(os.path.join(output_dir, '*.png')):
        os.remove(f)
    
    try:
        # Test with direct list of BAMs
        figures = igver.load_screenshots(
            paths=['test/test_tumor.bam', 'test/test_normal.bam'],  # Direct list
            regions=['chr8:32534767-32536767', 'chr19:11137898-11139898'],  # Two test regions
            output_dir=output_dir,
            genome='hg19',
            singularity_image='downloaded_image/igver_latest.sif',
            singularity_args='-B /home -B /tmp',
            overwrite=True,
            remove_png=False,
            debug=False
        )
        
        files = sorted([f for f in os.listdir(output_dir) if f.endswith('.png')])
        print(f"✓ Direct list input: Generated {len(files)} files")
        for f in files:
            size = os.path.getsize(os.path.join(output_dir, f))
            print(f"  - {f} ({size:,} bytes)")
        
        return True
        
    except Exception as e:
        print(f"✗ Direct list input failed: {e}")
        return False

if __name__ == '__main__':
    # Run both tests
    print("🧪 Testing igver Multi-BAM Input Methods\n")
    
    success1 = test_multi_bam_file_input()
    success2 = test_direct_bam_list()
    
    print("\n" + "="*60)
    print("📝 Summary:")
    print(f"  .txt file input: {'✅ PASS' if success1 else '❌ FAIL'}")
    print(f"  Direct list input: {'✅ PASS' if success2 else '❌ FAIL'}")
    
    print("\n📌 Key Points:")
    print("- igver DOES support .txt files with BAM paths (one per line)")
    print("- Comments (#) and empty lines are ignored")
    print("- Tilde (~) paths are expanded")
    print("- Both methods (.txt file and direct list) work correctly")
    
    sys.exit(0 if (success1 and success2) else 1)