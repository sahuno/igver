#!/usr/bin/env python3
"""
Test to verify igver Python package can generate IGV screenshots from a regions file.
"""

import igver
import os
import sys

def test_igver_screenshot():
    """Test if igver can generate screenshots from a multi-region file."""
    
    # Test inputs - using regions file with multiple coordinates
    test_bam = 'test/test_tumor.bam'
    regions_file = 'test_regions_multi.txt'  # File with multiple regions
    output_dir = '/tmp/igver_test'
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Read expected regions from file for verification
    with open(regions_file, 'r') as f:
        expected_regions = [line.strip() for line in f if line.strip()]
    
    print(f"Testing with {len(expected_regions)} regions from {regions_file}")
    
    try:
        # Generate screenshots from regions file
        figures = igver.load_screenshots(
            paths=[test_bam],
            regions=[regions_file],  # Pass the file path, not the regions directly
            output_dir=output_dir,
            genome='hg19',
            singularity_image='downloaded_image/igver_latest.sif',
            singularity_args='-B /home -B /tmp',
            overwrite=True,
            remove_png=False  # Keep PNGs to verify
        )
        
        # Check if PNGs were created for each region
        success_count = 0
        for region in expected_regions:
            # Convert region to expected filename format
            png_name = region.replace(':', '-') + '.png'
            expected_png = os.path.join(output_dir, png_name)
            
            if os.path.exists(expected_png):
                size = os.path.getsize(expected_png)
                if size > 0:
                    print(f"  ✓ {region} → {png_name} ({size:,} bytes)")
                    success_count += 1
                else:
                    print(f"  ✗ {region} → empty file")
            else:
                print(f"  ✗ {region} → file not created")
        
        if success_count == len(expected_regions):
            print(f"\n✅ PASS: All {success_count} screenshots generated successfully")
            return True
        else:
            print(f"\n❌ FAIL: Only {success_count}/{len(expected_regions)} screenshots generated")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False

if __name__ == '__main__':
    success = test_igver_screenshot()
    sys.exit(0 if success else 1)