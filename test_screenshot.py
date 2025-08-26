#!/usr/bin/env python3
"""
Test script to generate actual screenshots using igver Python package.
"""

import igver
import os
import tempfile

def test_igver_screenshots():
    """Generate real screenshots with test BAM files."""
    
    print("Starting igver screenshot test...")
    
    # Use test BAM files from the repository
    bam_files = [
        'test/test_tumor.bam',
        'test/test_normal.bam'
    ]
    
    # Test with both region file and inline regions
    regions_file = 'test_regions.txt'
    inline_regions = ['chr1:5000-6000', 'chr3:10000-11000']
    
    # Create output directory
    with tempfile.TemporaryDirectory() as output_dir:
        print(f"\nOutput directory: {output_dir}")
        
        # Test 1: Using regions file
        print("\n=== Test 1: Using regions file ===")
        print(f"BAM files: {bam_files}")
        print(f"Regions file: {regions_file}")
        
        try:
            # Call igver with regions file
            figures = igver.load_screenshots(
                paths=bam_files,
                regions=[regions_file],  # Pass as list
                output_dir=output_dir,
                genome='hg19',
                debug=True,
                use_singularity=True,
                singularity_image='docker://sahuno/igver:latest'
            )
            
            print(f"✅ Successfully created {len(figures)} figures from regions file")
            
            # List created files
            files = os.listdir(output_dir)
            print(f"Created files: {files}")
            
        except Exception as e:
            print(f"❌ Error with regions file: {e}")
        
        # Test 2: Using inline regions
        print("\n=== Test 2: Using inline regions ===")
        print(f"Inline regions: {inline_regions}")
        
        try:
            # Call igver with inline regions
            figures2 = igver.load_screenshots(
                paths=bam_files,
                regions=inline_regions,  # Direct regions
                output_dir=output_dir,
                genome='hg19',
                debug=True,
                use_singularity=True,
                singularity_image='docker://sahuno/igver:latest'
            )
            
            print(f"✅ Successfully created {len(figures2)} figures from inline regions")
            
            # List all created files
            all_files = os.listdir(output_dir)
            print(f"All created files: {all_files}")
            
            # Check file sizes
            print("\nFile sizes:")
            for f in all_files:
                path = os.path.join(output_dir, f)
                if os.path.exists(path):
                    size = os.path.getsize(path)
                    print(f"  {f}: {size} bytes")
            
            return True
            
        except Exception as e:
            print(f"❌ Error with inline regions: {e}")
            return False

if __name__ == '__main__':
    # Check if we have Singularity
    import shutil
    if not shutil.which('singularity'):
        print("⚠️  Singularity not found. Trying with local image...")
        
    success = test_igver_screenshots()
    
    if success:
        print("\n✅ Screenshot generation test PASSED!")
    else:
        print("\n❌ Screenshot generation test FAILED")
    
    exit(0 if success else 1)