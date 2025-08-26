#!/usr/bin/env python3
"""
Generate actual screenshots using igver with local Singularity image.
"""

import igver
import os
import shutil

print("Generating IGV screenshots with igver Python package...")

# Configuration
bam_files = ['test/test_tumor.bam', 'test/test_normal.bam'] 
regions = ['chr1:1000-2000', 'chr2:3000-4000']
output_dir = '/tmp/igver_screenshots'
local_sif = 'downloaded_image/igver_latest.sif'

# Clean and create output directory
if os.path.exists(output_dir):
    shutil.rmtree(output_dir)
os.makedirs(output_dir)

print(f"\nConfiguration:")
print(f"  BAM files: {bam_files}")
print(f"  Regions: {regions}")
print(f"  Output: {output_dir}")
print(f"  Singularity image: {local_sif}")

# Check if local image exists
if os.path.exists(local_sif):
    print(f"✅ Local Singularity image found: {local_sif}")
else:
    print(f"⚠️  Local image not found, will use Docker Hub")
    local_sif = 'docker://sahuno/igver:latest'

try:
    # Generate screenshots
    print("\nGenerating screenshots...")
    
    figures = igver.load_screenshots(
        paths=bam_files,
        regions=regions,
        output_dir=output_dir,
        genome='hg19',
        singularity_image=local_sif,
        singularity_args='-B /home -B /tmp',
        debug=False,  # Set to True for verbose output
        overwrite=True,
        remove_png=False  # Keep PNG files to verify
    )
    
    print(f"\n✅ Successfully generated {len(figures)} screenshots!")
    
    # List generated files
    files = os.listdir(output_dir)
    print(f"\nGenerated files in {output_dir}:")
    for f in sorted(files):
        if f.endswith('.png'):
            path = os.path.join(output_dir, f)
            size = os.path.getsize(path)
            print(f"  ✓ {f} ({size:,} bytes)")
    
    # Verify region names match
    print("\nVerifying region mapping:")
    for region in regions:
        expected = region.replace(':', '-')
        matching = [f for f in files if expected in f]
        if matching:
            print(f"  ✓ Region {region} → {matching[0]}")
        else:
            print(f"  ✗ Region {region} not found")
    
    print("\n🎉 SUCCESS! Screenshots generated with igver Python package")
    print(f"View them at: {output_dir}")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    
    # If error, still check if batch file was created
    batch_files = [f for f in os.listdir(output_dir) if f.endswith('.batch')]
    if batch_files:
        print(f"\nBatch file was created: {batch_files[0]}")
        with open(os.path.join(output_dir, batch_files[0]), 'r') as f:
            print("Content:")
            print(f.read())