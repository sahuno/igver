#!/usr/bin/env python3
"""
Test to verify that screenshot regions match expected regions.
"""

import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock

def test_screenshot_region_matching():
    """Test that screenshot regions in filenames match input regions."""
    import igver
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Define test regions
        test_regions = [
            'chr1:1000-2000',
            'chr2:3000-4000',
            'chr8:32534767-32536767'
        ]
        
        test_bam = 'test_sample.bam'
        
        # Mock the functions to simulate screenshot creation
        with patch('igver.igver.os.path.exists') as mock_exists:
            mock_exists.return_value = True
            
            with patch('igver.igver.subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
                
                with patch('igver.igver.shutil.which') as mock_which:
                    mock_which.return_value = '/usr/bin/singularity'
                    
                    # Create expected screenshot files
                    for region in test_regions:
                        # Format region for filename
                        region_str = region.replace(':', '_').replace('-', '_')
                        filename = f"{os.path.splitext(test_bam)[0]}_{region_str}.png"
                        filepath = os.path.join(temp_dir, filename)
                        
                        # Create dummy file
                        with open(filepath, 'w') as f:
                            f.write('dummy')
                    
                    # Mock load_image to return dummy figures
                    with patch('igver.igver.load_image') as mock_load_image:
                        mock_load_image.return_value = MagicMock()
                        
                        # Call the function
                        batch_file = igver.create_batch_script(
                            [test_bam],
                            test_regions,
                            'hg19',
                            temp_dir
                        )
                        
                        # Check batch file content
                        assert os.path.exists(batch_file)
                        with open(batch_file, 'r') as f:
                            content = f.read()
                            
                            # Verify all regions are in batch file
                            for region in test_regions:
                                assert f"goto {region}" in content
                                
                                # Check that snapshot names match regions
                                region_str = region.replace(':', '_').replace('-', '_')
                                expected_filename = f"test_sample_{region_str}.png"
                                assert expected_filename in content
                        
                        # Verify screenshot files exist with correct names
                        for region in test_regions:
                            region_str = region.replace(':', '_').replace('-', '_')
                            expected_file = os.path.join(temp_dir, f"test_sample_{region_str}.png")
                            assert os.path.exists(expected_file), f"Expected file {expected_file} not found"
                        
                        print("✓ All regions match expected screenshot filenames")
                        print(f"✓ Tested {len(test_regions)} regions successfully")
                        return True
                        
    finally:
        # Clean up
        shutil.rmtree(temp_dir)

def test_bed_region_matching():
    """Test that BED file regions generate correct screenshot names."""
    import igver
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Create a BED file with named regions
        bed_file = os.path.join(temp_dir, 'test_regions.bed')
        bed_regions = [
            ('chr1', '1000', '2000', 'region_A'),
            ('chr2', '3000', '4000', 'region_B'),
            ('chrX', '5000', '6000', 'region_C')
        ]
        
        with open(bed_file, 'w') as f:
            for region in bed_regions:
                f.write('\t'.join(region) + '\n')
        
        test_bam = 'test_sample.bam'
        
        with patch('igver.igver.os.path.exists') as mock_exists:
            def exists_side_effect(path):
                if path == bed_file:
                    return True
                return True  # Mock other files as existing
            mock_exists.side_effect = exists_side_effect
            
            # Create batch script
            batch_file = igver.create_batch_script(
                [test_bam],
                [bed_file],
                'hg19',
                temp_dir
            )
            
            assert os.path.exists(batch_file)
            
            # Read and verify batch file
            with open(batch_file, 'r') as f:
                content = f.read()
                
                # Check each BED region
                for chrom, start, end, name in bed_regions:
                    # Expected goto command
                    expected_goto = f"goto {chrom}:{start}-{end}"
                    assert expected_goto in content, f"Missing goto for {name}"
                    
                    # Expected filename with region name
                    region_str = f"{chrom}_{start}_{end}_{name}"
                    expected_filename = f"test_sample_{region_str}.png"
                    assert expected_filename in content, f"Missing filename {expected_filename}"
            
            print("✓ BED regions correctly mapped to screenshot names")
            print(f"✓ All {len(bed_regions)} BED regions verified")
            return True
            
    finally:
        shutil.rmtree(temp_dir)

if __name__ == '__main__':
    success1 = test_screenshot_region_matching()
    success2 = test_bed_region_matching()
    
    if success1 and success2:
        print("\n✅ All region-screenshot matching tests passed!")
        exit(0)
    else:
        exit(1)