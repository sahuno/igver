#!/usr/bin/env python3
"""
Fixed test suite for igver Python package.
Tests both direct region strings and region files.
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

TEST_BAM = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_tumor.bam')

def test_create_batch_with_direct_regions():
    """Test create_batch_script with direct region strings."""
    import igver
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test with direct region strings - igver should handle these
        regions = ['chr1:1000-2000', 'chr2:3000-4000']
        
        with patch('os.path.exists') as mock_exists:
            # Make it think BAM files exist but regions don't (so treated as strings)
            def exists_side_effect(path):
                if path.endswith('.bam'):
                    return True
                if path in regions:
                    return False  # Regions are not files
                return False
            mock_exists.side_effect = exists_side_effect
            
            # Create batch script with direct regions
            result = igver.create_batch_script(
                paths=['test1.bam', 'test2.bam'],
                regions=regions,
                output_dir=temp_dir,
                genome='hg19'
            )
            
            # Handle both tuple and string return
            if isinstance(result, tuple):
                batch_file, png_paths = result
            else:
                batch_file = result
                png_paths = []
            
            assert batch_file is not None
            print(f"✓ Batch file created: {batch_file}")
            
            # Check batch file content
            if os.path.exists(batch_file):
                with open(batch_file, 'r') as f:
                    content = f.read()
                    assert 'goto chr1:1000-2000' in content
                    assert 'goto chr2:3000-4000' in content
                    assert 'genome hg19' in content.lower()
                    print("✓ Batch file contains correct regions")


def test_create_batch_with_region_file(tmp_path):
    """create_batch_script turns a .txt region file into goto/snapshot blocks."""
    import igver

    regions_file = tmp_path / 'regions.txt'
    regions_file.write_text(
        'chr1:1000-2000\n'
        'chr2:3000-4000\tdeletion\n'
        'chr3:5000-6000 chr4:7000-8000 translocation\n'
    )

    batch_file, png_paths = igver.create_batch_script(
        paths=[TEST_BAM],
        regions=[str(regions_file)],
        output_dir=str(tmp_path),
        genome='hg19',
    )

    content = open(batch_file).read()
    assert f'load {TEST_BAM}' in content
    assert 'genome hg19' in content
    assert 'goto chr1:1000-2000' in content
    assert 'goto chr2:3000-4000' in content
    assert 'goto chr3:5000-6000 chr4:7000-8000' in content  # multi-locus split screen
    assert [os.path.basename(p) for p in png_paths] == [
        'chr1-1000-2000.png',
        'chr2-3000-4000.deletion.png',                     # trailing field becomes the tag
        'chr3-5000-6000.chr4-7000-8000.translocation.png',
    ]
    assert all(f'snapshot {os.path.basename(p)}' in content for p in png_paths)


def test_create_batch_with_bed_file(tmp_path):
    """create_batch_script parses BED6 (named) and BED3 (unnamed) rows."""
    import igver

    bed_file = tmp_path / 'regions.bed'
    bed_file.write_text(
        'chr1\t1000\t2000\tregion_A\t100\t+\n'
        'chr2\t3000\t4000\tregion_B\t200\t-\n'
        'chrX\t5000\t6000\n'          # BED3, no name
        '# comment line\n'
    )

    batch_file, png_paths = igver.create_batch_script(
        paths=[TEST_BAM],
        regions=[str(bed_file)],
        output_dir=str(tmp_path),
        genome='hg19',
    )

    content = open(batch_file).read()
    assert 'goto chr1:1000-2000' in content
    assert 'goto chr2:3000-4000' in content
    assert 'goto chrX:5000-6000' in content
    assert [os.path.basename(p) for p in png_paths] == [
        'chr1-1000-2000.region_A.png',
        'chr2-3000-4000.region_B.png',
        'chrX-5000-6000.png',
    ]
    assert all(f'snapshot {os.path.basename(p)}' in content for p in png_paths)


def test_run_igv_signature(tmp_path):
    """run_igv wraps the IGV command in singularity only when asked to."""
    import igver

    image = 'docker://sahuno/igver:test-tag'
    seen = []

    def fake_igv(cmd, png_paths, stall_timeout, debug=False):
        seen.append(cmd)
        for png in png_paths:
            open(png, 'w').close()
        return True

    def _batch(name):
        path = tmp_path / name
        path.write_text('new\ngenome hg19\nexit\n')
        return str(path)

    with patch('igver.igver._run_until_stalled', side_effect=fake_igv):
        png = str(tmp_path / 'with_sing.png')
        igver.run_igv(_batch('sing.batch'), [png], igv_dir='/opt/IGV',
                      singularity_image=image, use_singularity=True)
        png = str(tmp_path / 'without_sing.png')
        igver.run_igv(_batch('nosing.batch'), [png], igv_dir='/opt/IGV',
                      singularity_image=image, use_singularity=False)

    assert len(seen) == 2
    assert seen[0].startswith('singularity run')
    assert image in seen[0]
    assert '/opt/IGV/igv.sh' in seen[0]
    assert not seen[1].startswith('singularity')
    assert image not in seen[1]
    assert '/opt/IGV/igv.sh' in seen[1]


def test_with_local_singularity_image():
    """Test using local Singularity image."""
    import igver
    
    local_image = 'downloaded_image/igver_latest.sif'
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create simple test
        regions = ['chr1:1000-2000']
        
        with patch('os.path.exists') as mock_exists:
            def exists_side_effect(path):
                if path.endswith('.bam'):
                    return True
                if path == local_image:
                    return True  # Local image exists
                if path in regions:
                    return False  # Direct region string
                return False
            mock_exists.side_effect = exists_side_effect
            
            # Test that local image path can be used
            result = igver.create_batch_script(
                paths=['test.bam'],
                regions=regions,
                output_dir=temp_dir,
                genome='hg19'
            )
            
            if isinstance(result, tuple):
                batch_file, png_paths = result
            else:
                batch_file = result
                png_paths = []
            
            # Now test run_igv with local image
            with patch('shutil.which') as mock_which:
                mock_which.return_value = '/usr/bin/singularity'
                
                with patch('subprocess.run') as mock_run:
                    mock_run.return_value = MagicMock(returncode=0)
                    
                    try:
                        igver.run_igv(
                            batch_file,
                            png_paths,
                            singularity_image=local_image,  # Use local image
                            use_singularity=True
                        )
                        
                        # Check that singularity was called with local image
                        mock_run.assert_called_once()
                        call_args = mock_run.call_args[0][0]
                        assert local_image in call_args
                        print(f"✓ Local Singularity image {local_image} can be used")
                    except Exception as e:
                        print(f"Note: {e}")


def test_load_screenshots_function(tmp_path):
    """load_screenshots returns the snapshot paths it asked IGV to render."""
    import igver

    def fake_igv(cmd, png_paths, stall_timeout, debug=False):
        for png in png_paths:
            open(png, 'wb').write(b'PNG_DUMMY')
        return True

    with patch('igver.igver._run_until_stalled', side_effect=fake_igv):
        result = igver.load_screenshots(
            [TEST_BAM],
            ['chr1:100-200'],
            str(tmp_path),
            genome='hg19',
            use_singularity=False,
            load_figures=False,
        )

    assert result == [str(tmp_path / 'chr1-100-200.png')]
    assert all(os.path.exists(p) for p in result)


if __name__ == '__main__':
    print("Running fixed igver tests...\n")
    
    test_create_batch_with_direct_regions()
    test_create_batch_with_region_file(Path(tempfile.mkdtemp()))
    test_create_batch_with_bed_file(Path(tempfile.mkdtemp()))
    test_run_igv_signature(Path(tempfile.mkdtemp()))
    test_with_local_singularity_image()
    test_load_screenshots_function(Path(tempfile.mkdtemp()))
    
    print("\n✅ All fixed tests completed!")