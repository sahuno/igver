import os

from .igver import load_screenshots, run_igv, create_batch_script

try:
    from importlib.metadata import PackageNotFoundError, version
except ImportError:  # For Python <3.8
    from importlib_metadata import PackageNotFoundError, version

try:
    __version__ = version("igver")
except PackageNotFoundError:  # running from a source checkout, not installed
    __version__ = "0+unknown"
__file__ = os.path.abspath(__file__)  # Store absolute path of this file
__all__ = ["load_screenshots", "run_igv", "create_batch_script"]
