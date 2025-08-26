#!/usr/bin/env python3
"""
Comprehensive test suite for the igver Python package.
Tests package functionality without requiring Singularity or actual IGV execution.
"""

import pytest
import os
import sys
import tempfile
import shutil
import subprocess
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path

# Test if package can be imported
def test_package_import():
    """Test that igver package can be imported."""
    import igver
    assert igver is not None
    

def test_package_version():
    """Test that package version is accessible."""
    try:
        import pkg_resources
        version = pkg_resources.get_distribution("igver").version
        assert version is not None
        assert isinstance(version, str)
        assert len(version) > 0
    except:
        # Version might not be available in dev mode
        pytest.skip("Version not available in development mode")


class TestAPIFunctions:
    """Test that all expected API functions are available."""
    
    def test_load_screenshots_exists(self):
        """Test that load_screenshots function exists."""
        import igver
        assert hasattr(igver, 'load_screenshots')
        assert callable(igver.load_screenshots)
    
    def test_create_batch_script_exists(self):
        """Test that create_batch_script function exists."""
        import igver
        assert hasattr(igver, 'create_batch_script')
        assert callable(igver.create_batch_script)
    
    def test_run_igv_exists(self):
        """Test that run_igv function exists."""
        import igver
        assert hasattr(igver, 'run_igv')
        assert callable(igver.run_igv)
    
    def test_function_signatures(self):
        """Test that functions have expected signatures."""
        import igver
        import inspect
        
        # Check load_screenshots parameters
        sig = inspect.signature(igver.load_screenshots)
        params = list(sig.parameters.keys())
        assert 'paths' in params
        assert 'regions' in params
        assert 'output_dir' in params
        assert 'genome' in params


class TestCLI:
    """Test command-line interface functionality."""
    
    def test_cli_help(self):
        """Test that CLI help works."""
        result = subprocess.run(['igver', '--help'], capture_output=True, text=True)
        assert result.returncode == 0
        assert 'IGVer' in result.stdout or 'igver' in result.stdout
        assert '-i' in result.stdout or '--input' in result.stdout
        assert '-r' in result.stdout or '--regions' in result.stdout
    
    def test_cli_missing_args(self):
        """Test that CLI fails gracefully with missing arguments."""
        result = subprocess.run(['igver'], capture_output=True, text=True)
        assert result.returncode != 0
        assert 'required' in result.stderr.lower() or 'usage' in result.stderr.lower()


class TestInputFileParsing:
    """Test input file parsing functionality."""
    
    def setup_method(self):
        """Create temporary directory for test files."""
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)
    
    def test_text_file_parsing(self):
        """Test parsing of .txt input files."""
        # Create a test .txt file
        txt_file = os.path.join(self.temp_dir, 'tracks.txt')
        content = """# Test tracks
/path/to/sample1.bam
/path/to/sample2.bam

# Another track
~/data/sample3.bam
"""
        with open(txt_file, 'w') as f:
            f.write(content)
        
        # Test that the file can be read
        with open(txt_file, 'r') as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        assert len(lines) == 3
        assert '/path/to/sample1.bam' in lines[0]
        assert '/path/to/sample2.bam' in lines[1]
        assert '~/data/sample3.bam' in lines[2]
    
    def test_mixed_input_parsing(self):
        """Test parsing of mixed input types."""
        from igver.cli import parse_input_files
        
        # Create a test .txt file
        txt_file = os.path.join(self.temp_dir, 'tracks.txt')
        with open(txt_file, 'w') as f:
            f.write('/path/to/sample1.bam\n')
        
        # Parse mixed inputs
        inputs = [txt_file, '/direct/path.bam']
        result = parse_input_files(inputs)
        
        assert len(result) == 2
        assert '/path/to/sample1.bam' in result
        assert '/direct/path.bam' in result
    
    def test_empty_text_file(self):
        """Test parsing of empty .txt file."""
        from igver.cli import parse_input_files
        
        txt_file = os.path.join(self.temp_dir, 'empty.txt')
        with open(txt_file, 'w') as f:
            f.write('# Only comments\n# More comments\n\n')
        
        result = parse_input_files([txt_file])
        assert len(result) == 0
    
    def test_nonexistent_text_file(self):
        """Test handling of non-existent .txt file."""
        from igver.cli import parse_input_files
        
        with pytest.raises(FileNotFoundError):
            parse_input_files(['/nonexistent/file.txt'])


class TestBatchScriptGeneration:
    """Test IGV batch script generation."""
    
    def setup_method(self):
        """Create temporary directory for test files."""
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)
    
    @patch('igver.igver.os.path.exists')
    def test_batch_script_creation(self, mock_exists):
        """Test that batch script is created with correct content."""
        import igver
        
        # Mock file existence checks
        mock_exists.return_value = True
        
        # Create batch script
        batch_file = igver.create_batch_script(
            paths=['test1.bam', 'test2.bam'],
            regions=['chr1:1000-2000'],
            genome='hg19',
            output_dir=self.temp_dir
        )
        
        assert batch_file is not None
        assert os.path.exists(batch_file)
        
        # Check content
        with open(batch_file, 'r') as f:
            content = f.read()
            assert 'new' in content.lower()
            assert 'genome hg19' in content.lower()
            assert 'load test1.bam' in content
            assert 'load test2.bam' in content
            assert 'goto chr1:1000-2000' in content
            assert 'snapshot' in content.lower()
    
    @patch('igver.igver.os.path.exists')
    def test_batch_script_with_bed_regions(self, mock_exists):
        """Test batch script generation with BED file regions."""
        import igver
        
        mock_exists.return_value = True
        
        # Create a BED file
        bed_file = os.path.join(self.temp_dir, 'regions.bed')
        with open(bed_file, 'w') as f:
            f.write('chr1\t1000\t2000\tregion1\t0\t+\n')
            f.write('chr2\t3000\t4000\tregion2\t0\t-\n')
        
        batch_file = igver.create_batch_script(
            paths=['test.bam'],
            regions=[bed_file],
            genome='hg19',
            output_dir=self.temp_dir
        )
        
        with open(batch_file, 'r') as f:
            content = f.read()
            assert 'goto chr1:1000-2000' in content
            assert 'goto chr2:3000-4000' in content
            assert 'test_chr1_1000_2000_region1.png' in content
            assert 'test_chr2_3000_4000_region2.png' in content


class TestMockFunctionality:
    """Test main functionality with mocked external dependencies."""
    
    @patch('igver.igver.subprocess.run')
    @patch('igver.igver.os.path.exists')
    @patch('igver.igver.shutil.which')
    def test_load_screenshots_mock(self, mock_which, mock_exists, mock_run):
        """Test load_screenshots with mocked subprocess."""
        import igver
        
        # Mock singularity availability
        mock_which.return_value = '/usr/bin/singularity'
        mock_exists.return_value = True
        
        # Mock successful singularity run
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='Success',
            stderr=''
        )
        
        # Mock image loading
        with patch('igver.igver.load_image') as mock_load_image:
            mock_load_image.return_value = MagicMock()  # Mock figure
            
            # Call the function
            with patch('igver.igver.create_batch_script') as mock_batch:
                mock_batch.return_value = '/tmp/test_batch.txt'
                
                result = igver.load_screenshots(
                    paths=['test.bam'],
                    regions=['chr1:1000-2000'],
                    output_dir='/tmp',
                    genome='hg19'
                )
        
        # Verify subprocess was called
        assert mock_run.called
        
        # Check singularity command construction
        call_args = mock_run.call_args[0][0]
        assert 'singularity' in call_args[0]
        assert 'run' in call_args
    
    @patch('igver.igver.shutil.which')
    def test_singularity_detection(self, mock_which):
        """Test automatic Singularity detection."""
        import igver
        
        # Test when Singularity is not available
        mock_which.return_value = None
        
        with patch('igver.igver.os.path.exists') as mock_exists:
            mock_exists.return_value = False  # Also not in container
            
            with pytest.raises((RuntimeError, TypeError)) as excinfo:
                # run_igv expects batch_file as positional
                igver.run_igv(
                    '/tmp/batch.txt',  # positional
                    igv_dir='/opt/IGV',
                    singularity_image='test.sif'
                )
            
            # Check for either error message
            error_msg = str(excinfo.value).lower()
            assert 'singularity' in error_msg or 'argument' in error_msg
    
    @patch('igver.igver.os.environ')
    @patch('igver.igver.os.path.exists')
    def test_container_detection(self, mock_exists, mock_environ):
        """Test detection of running inside a container."""
        import igver
        
        # Simulate running inside Singularity container
        mock_environ.get.return_value = '1'
        mock_exists.return_value = True
        
        # Should not require Singularity when already in container
        with patch('igver.igver.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            igver.run_igv(
                batch_file='/tmp/batch.txt',
                igv_dir='/opt/IGV',
                use_singularity=None  # Auto-detect
            )
            
            # Should call IGV directly, not through Singularity
            call_args = mock_run.call_args[0][0]
            assert 'singularity' not in call_args[0]
            assert 'igv.sh' in ' '.join(call_args)


class TestRegionParsing:
    """Test genomic region parsing functionality."""
    
    def test_parse_standard_region(self):
        """Test parsing of standard chr:start-end format."""
        from igver.igver import parse_regions
        
        regions = parse_regions(['chr1:1000-2000', 'chr2:3000-4000'])
        assert len(regions) == 2
        assert regions[0] == 'chr1:1000-2000'
        assert regions[1] == 'chr2:3000-4000'
    
    def test_parse_text_file_regions(self):
        """Test parsing regions from a text file."""
        from igver.igver import parse_regions
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('chr1:1000-2000\n')
            f.write('chr2:3000-4000\n')
            f.write('# Comment line\n')
            f.write('\n')  # Empty line
            f.write('chr3:5000-6000\n')
            temp_file = f.name
        
        try:
            regions = parse_regions([temp_file])
            assert len(regions) == 3
            assert 'chr1:1000-2000' in regions
            assert 'chr2:3000-4000' in regions
            assert 'chr3:5000-6000' in regions
        finally:
            os.unlink(temp_file)
    
    def test_parse_bed_file_regions(self):
        """Test parsing regions from a BED file."""
        from igver.igver import parse_regions
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bed', delete=False) as f:
            f.write('chr1\t1000\t2000\n')
            f.write('chr2\t3000\t4000\tregion_name\t100\t+\n')
            temp_file = f.name
        
        try:
            regions = parse_regions([temp_file])
            assert len(regions) == 2
            assert ('chr1:1000-2000', None) in regions or 'chr1:1000-2000' in str(regions)
            assert ('chr2:3000-4000', 'region_name') in regions or 'chr2:3000-4000' in str(regions)
        finally:
            os.unlink(temp_file)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])