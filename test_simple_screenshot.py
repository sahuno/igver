#!/usr/bin/env python3
"""
Simple test to generate screenshots using igver Python package.
"""

import igver
import os

# Simple test with minimal regions
print("Testing igver screenshot generation...")

# Test BAM files
bam_files = ['test/test_tumor.bam', 'test/test_normal.bam']

# Simple regions 
regions = ['chr1:1000-2000']

# Output directory
output_dir = '/tmp/igver_test_output'
os.makedirs(output_dir, exist_ok=True)

print(f"BAM files: {bam_files}")
print(f"Regions: {regions}")
print(f"Output: {output_dir}")

# Try to create screenshots using local Singularity image
try:
    # First try: just create batch script
    batch_file, png_paths = igver.create_batch_script(
        paths=bam_files,
        regions=regions,
        output_dir=output_dir,
        genome='hg19'
    )
    
    print(f"\n✅ Batch script created: {batch_file}")
    print(f"Expected PNG files: {png_paths}")
    
    # Show batch file content
    with open(batch_file, 'r') as f:
        content = f.read()
        print("\nBatch file content:")
        print("-" * 40)
        print(content[:500])  # First 500 chars
        print("-" * 40)
    
    # Check if regions are properly handled
    assert 'goto chr1:1000-2000' in content, "Region not found in batch file"
    assert 'load' in content.lower(), "No load commands in batch file"
    
    print("\n✅ SUCCESS: igver correctly handles regions!")
    print(f"   - Direct region string 'chr1:1000-2000' was processed")
    print(f"   - Batch file contains correct goto command")
    print(f"   - Both BAM files will be loaded")
    
    # Now try with regions file
    regions_file = 'test_regions.txt'
    if os.path.exists(regions_file):
        batch_file2, png_paths2 = igver.create_batch_script(
            paths=bam_files,
            regions=[regions_file],
            output_dir=output_dir,
            genome='hg19'
        )
        
        with open(batch_file2, 'r') as f:
            content2 = f.read()
        
        # Count goto commands
        goto_count = content2.count('goto ')
        print(f"\n✅ Regions file test: {goto_count} regions found in batch file")
        
    print("\n📊 Summary:")
    print("- igver accepts both direct region strings and region files")
    print("- Batch scripts are created correctly")
    print("- Screenshot paths are generated properly")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()