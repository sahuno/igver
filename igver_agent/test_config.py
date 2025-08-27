"""
Test configuration for IGVer Agent
Centralizes test settings and paths
"""

import os
from pathlib import Path

# Base directories
AGENT_DIR = Path(__file__).parent
TEST_RESULTS_DIR = AGENT_DIR / "test_results"
TEST_DATA_DIR = AGENT_DIR.parent / "test"

# Ensure test results directory exists
TEST_RESULTS_DIR.mkdir(exist_ok=True)

# Test subdirectories
TEST_DIRS = {
    'logic': TEST_RESULTS_DIR / 'logic_test',
    'openai': TEST_RESULTS_DIR / 'openai_test', 
    'anthropic': TEST_RESULTS_DIR / 'anthropic_test',
    'tagged': TEST_RESULTS_DIR / 'tagged_regions_test',
    'batch': TEST_RESULTS_DIR / 'batch_test',
    'example': TEST_RESULTS_DIR / 'example_run'
}

# Test BAM files
TEST_BAMS = {
    'normal': TEST_DATA_DIR / 'test_normal.bam',
    'tumor': TEST_DATA_DIR / 'test_tumor.bam'
}

# Test region files
TEST_REGION_FILES = {
    'basic': TEST_DATA_DIR / 'regions.txt',
    'tagged': AGENT_DIR.parent / 'test_regions_tagged.txt',
    'multi': AGENT_DIR.parent / 'test_regions_multi.txt'
}

# Test regions for quick tests
QUICK_TEST_REGIONS = [
    "chr8:32534767-32536767",
    "chr19:11137898-11139898"
]

# Cancer gene test regions
CANCER_TEST_REGIONS = [
    "chr17:43044295-43045802",   # BRCA1
    "chr13:32315086-32400266",   # BRCA2
    "chr9:21967752-21975098",    # CDKN2A
    "chr17:7571720-7579721"      # TP53
]

# Singularity images to try in order
SINGULARITY_IMAGES = [
    AGENT_DIR.parent / "downloaded_image/igver_latest.sif",
    "/tmp/igver_latest.sif",
    "docker://sahuno/igver:latest"
]

def get_test_output_dir(test_name: str) -> Path:
    """Get or create test output directory"""
    if test_name not in TEST_DIRS:
        TEST_DIRS[test_name] = TEST_RESULTS_DIR / test_name
    
    output_dir = TEST_DIRS[test_name]
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

def get_singularity_image():
    """Find available Singularity image"""
    for image in SINGULARITY_IMAGES:
        if isinstance(image, Path):
            if image.exists():
                return str(image)
        elif image.startswith("docker://"):
            return image
    
    # Default to docker if nothing found
    return "docker://sahuno/igver:latest"

def get_valid_bam_files():
    """Return list of valid BAM files that exist"""
    valid_bams = []
    for name, path in TEST_BAMS.items():
        if path.exists():
            valid_bams.append(str(path))
    return valid_bams

def cleanup_old_results(keep_latest: int = 5):
    """Clean up old test results, keeping only the latest N runs"""
    import shutil
    from datetime import datetime
    
    for test_dir in TEST_RESULTS_DIR.iterdir():
        if not test_dir.is_dir():
            continue
            
        # Get all session directories with timestamps
        sessions = []
        for session in test_dir.iterdir():
            if session.is_dir():
                try:
                    # Try to get modification time
                    mtime = session.stat().st_mtime
                    sessions.append((mtime, session))
                except:
                    pass
        
        # Sort by modification time
        sessions.sort(reverse=True)
        
        # Remove old sessions
        for _, session in sessions[keep_latest:]:
            try:
                shutil.rmtree(session)
                print(f"Removed old test results: {session}")
            except Exception as e:
                print(f"Failed to remove {session}: {e}")

def summarize_test_results():
    """Print summary of all test results"""
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    for test_name, test_dir in TEST_DIRS.items():
        if not test_dir.exists():
            continue
            
        print(f"\n📁 {test_name}:")
        
        # Count files
        png_files = list(test_dir.rglob("*.png"))
        json_files = list(test_dir.rglob("*.json"))
        html_files = list(test_dir.rglob("*.html"))
        
        print(f"  Screenshots: {len(png_files)}")
        print(f"  JSON reports: {len(json_files)}")
        print(f"  HTML reports: {len(html_files)}")
        
        # Check for latest results
        if json_files:
            latest = max(json_files, key=lambda x: x.stat().st_mtime)
            print(f"  Latest: {latest.name}")
    
    # Total disk usage
    total_size = sum(f.stat().st_size for f in TEST_RESULTS_DIR.rglob("*") if f.is_file())
    print(f"\n💾 Total disk usage: {total_size / 1024 / 1024:.1f} MB")
    print("=" * 60)

if __name__ == "__main__":
    # When run directly, show test configuration
    print("🧬 IGVer Agent Test Configuration")
    print("=" * 40)
    print(f"Test results directory: {TEST_RESULTS_DIR}")
    print(f"Test data directory: {TEST_DATA_DIR}")
    print(f"Singularity image: {get_singularity_image()}")
    print(f"\nAvailable BAM files:")
    for bam in get_valid_bam_files():
        print(f"  ✅ {bam}")
    
    # Show results summary
    summarize_test_results()
    
    # Optionally cleanup old results
    # cleanup_old_results(keep_latest=3)