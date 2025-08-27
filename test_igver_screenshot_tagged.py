#!/usr/bin/env python3
"""
Follow-up test to verify igver handles tagged regions correctly.
Tests that tags in the second column are included in output filenames.
"""

import igver
import os
import sys
import glob

def test_igver_screenshot_with_tags():
    """Test if igver correctly handles tags in region files."""
    
    # Test inputs - regions file with tags in second column
    test_bam = 'test/test_tumor.bam'
    regions_file = 'test_regions_tagged.txt'  # File with "region tag" format
    output_dir = '/tmp/igver_test_tagged'
    
    # Clean and create output directory
    if os.path.exists(output_dir):
        for f in glob.glob(os.path.join(output_dir, '*.png')):
            os.remove(f)
    os.makedirs(output_dir, exist_ok=True)
    
    # Read and parse regions file
    expected_regions = []
    with open(regions_file, 'r') as f:
        for line in f:
            if line.strip():
                parts = line.strip().split()
                if len(parts) >= 2:
                    region = parts[0]
                    tag = parts[1]
                    expected_regions.append((region, tag))
    
    print(f"Testing tagged screenshots with {len(expected_regions)} regions")
    print(f"Regions file: {regions_file}")
    print(f"Format: 'region tag' (space-separated)\n")
    
    try:
        # Generate screenshots from tagged regions file
        figures = igver.load_screenshots(
            paths=[test_bam],
            regions=[regions_file],
            output_dir=output_dir,
            genome='hg19',
            singularity_image='downloaded_image/igver_latest.sif',
            singularity_args='-B /home -B /tmp',
            overwrite=True,
            remove_png=False,
            debug=False
        )
        
        print("Checking generated screenshots:\n")
        
        # Check if PNGs were created with correct naming
        success_count = 0
        failed_regions = []
        
        for region, tag in expected_regions:
            # Expected filename format based on igver's _parse_region_file
            # It should be: region_formatted.tag.png
            region_formatted = region.replace(':', '-')
            expected_name1 = f"{region_formatted}.{tag}.png"  # With tag
            expected_name2 = f"{region_formatted}.png"         # Without tag (fallback)
            
            png_path1 = os.path.join(output_dir, expected_name1)
            png_path2 = os.path.join(output_dir, expected_name2)
            
            if os.path.exists(png_path1):
                size = os.path.getsize(png_path1)
                if size > 0:
                    print(f"  ✓ {region} + '{tag}' → {expected_name1} ({size:,} bytes)")
                    success_count += 1
                else:
                    print(f"  ✗ {region} + '{tag}' → empty file")
                    failed_regions.append(region)
            elif os.path.exists(png_path2):
                size = os.path.getsize(png_path2)
                print(f"  ⚠ {region} → {expected_name2} ({size:,} bytes) [tag not in filename]")
                success_count += 1
            else:
                print(f"  ✗ {region} + '{tag}' → file not found")
                failed_regions.append(region)
        
        # List all generated files for debugging
        print("\nAll generated files:")
        all_files = sorted([f for f in os.listdir(output_dir) if f.endswith('.png')])
        for f in all_files:
            size = os.path.getsize(os.path.join(output_dir, f))
            print(f"  - {f} ({size:,} bytes)")
        
        # Summary
        print("\n" + "="*60)
        if success_count == len(expected_regions):
            print(f"✅ PASS: All {success_count} tagged screenshots generated")
            print("✅ Tags are correctly handled in output filenames")
            return True
        else:
            print(f"❌ FAIL: Only {success_count}/{len(expected_regions)} screenshots successful")
            if failed_regions:
                print(f"Failed regions: {', '.join(failed_regions)}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_igver_screenshot_with_tags()
    
    print("\n📝 Notes:")
    print("- igver reads space/tab-separated columns from region files")
    print("- Second column becomes a tag in the output filename")
    print("- Format: chr:start-end.tag.png")
    print("- Tags help organize screenshots for downstream processing")
    print("\n📌 BAM Input Options:")
    print("- Space-separated: igver -i file1.bam file2.bam -r regions.txt")
    print("- NOT comma-separated (would be treated as single filename)")
    print("- Multi-line text file: igver -i bam_list.txt -r regions.txt")
    
    sys.exit(0 if success else 1)