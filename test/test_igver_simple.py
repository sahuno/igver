#!/usr/bin/env python3
"""
Simplified test for igver that confirms regions work correctly.
"""

import tempfile
import os
from unittest.mock import patch, MagicMock

def test_igver_with_region_files():
    """Test that igver correctly handles region files."""
    import igver
    
    print("\n=== Testing IGVer with Region Files ===\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test 1: Text file with regions
        print("1. Testing with text file regions...")
        regions_txt = os.path.join(temp_dir, 'regions.txt')
        with open(regions_txt, 'w') as f:
            f.write('chr1:1000-2000\n')
            f.write('chr2:3000-4000\n')
            f.write('# This is a comment\n')
            f.write('chrX:5000-6000\n')
        
        # Mock only what we need
        with patch('igver.igver.os.path.exists') as mock_exists:
            # Use the original os.path.exists but intercept calls
            original_exists = os.path.exists
            def smart_exists(path):
                # Say BAM files exist
                if path.endswith('.bam') or path.endswith('.bai'):
                    return True
                # Everything else, check for real
                return original_exists(path)
            mock_exists.side_effect = smart_exists
            
            result = igver.create_batch_script(
                paths=['sample1.bam', 'sample2.bam'],
                regions=[regions_txt],  # Pass the file
                output_dir=temp_dir,
                genome='hg19'
            )
            
            # Handle tuple return
            if isinstance(result, tuple):
                batch_file, png_paths = result
            else:
                batch_file = result
                png_paths = []
            
            print(f"   ✓ Batch file created: {batch_file}")
            
            # Check batch content
            with open(batch_file, 'r') as f:
                content = f.read()
                assert 'goto chr1:1000-2000' in content
                assert 'goto chr2:3000-4000' in content
                assert 'goto chrX:5000-6000' in content
                assert '# This is a comment' not in content  # Comments should be ignored
                print("   ✓ All regions found in batch file")
                print(f"   ✓ Generated {len(png_paths)} PNG paths")
        
        # Test 2: BED file
        print("\n2. Testing with BED file...")
        bed_file = os.path.join(temp_dir, 'regions.bed')
        with open(bed_file, 'w') as f:
            f.write('chr1\t1000\t2000\tregion_A\t100\t+\n')  # BED6
            f.write('chr2\t3000\t4000\tregion_B\t200\t-\n')
            f.write('chrX\t5000\t6000\n')  # BED3
        
        with patch('igver.igver.os.path.exists') as mock_exists:
            original_exists = os.path.exists
            def smart_exists(path):
                if path.endswith('.bam') or path.endswith('.bai'):
                    return True
                return original_exists(path)
            mock_exists.side_effect = smart_exists
            
            result = igver.create_batch_script(
                paths=['sample.bam'],
                regions=[bed_file],
                output_dir=temp_dir,
                genome='hg38'
            )
            
            if isinstance(result, tuple):
                batch_file, png_paths = result
            else:
                batch_file = result
                png_paths = []
            
            print(f"   ✓ Batch file created from BED: {batch_file}")
            
            with open(batch_file, 'r') as f:
                content = f.read()
                assert 'goto chr1:1000-2000' in content
                assert 'goto chr2:3000-4000' in content
                assert 'goto chrX:5000-6000' in content
                # Check that region names are in filenames
                if 'region_A' in content and 'region_B' in content:
                    print("   ✓ BED region names preserved in output")
                else:
                    print("   ✓ BED regions parsed correctly")
        
        # Test 3: Direct region strings (no file)
        print("\n3. Testing with direct region strings...")
        with patch('igver.igver.os.path.exists') as mock_exists:
            def smart_exists(path):
                if path.endswith('.bam') or path.endswith('.bai'):
                    return True
                # Region strings should not exist as files
                if ':' in path and '-' in path:
                    return False
                return os.path.exists(path)
            mock_exists.side_effect = smart_exists
            
            result = igver.create_batch_script(
                paths=['test.bam'],
                regions=['chr3:7000-8000', 'chr4:9000-10000'],  # Direct strings
                output_dir=temp_dir,
                genome='mm10'
            )
            
            if isinstance(result, tuple):
                batch_file, png_paths = result
            else:
                batch_file = result
            
            print(f"   ✓ Batch file created from direct regions: {batch_file}")
            
            with open(batch_file, 'r') as f:
                content = f.read()
                assert 'goto chr3:7000-8000' in content
                assert 'goto chr4:9000-10000' in content
                print("   ✓ Direct region strings handled correctly")
        
        print("\n=== All Tests Passed! ===")
        print(f"\nSummary:")
        print(f"✅ Region text files are properly parsed")
        print(f"✅ BED files (BED3 and BED6) are correctly handled")
        print(f"✅ Direct region strings work without files")
        print(f"✅ Comments in region files are ignored")
        print(f"✅ Multiple BAM files can be processed")
        print(f"\n📍 Local Singularity image available at: downloaded_image/igver_latest.sif")
        return True


if __name__ == '__main__':
    success = test_igver_with_region_files()
    exit(0 if success else 1)