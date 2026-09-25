import gzip
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
import uuid
import time

try:
    from importlib import resources  # Python 3.9+
except ImportError:
    import importlib_resources as resources  # Backport for Python 3.7-3.8

from PIL import Image
import matplotlib.pyplot as plt
try:
    import cairosvg
    HAS_CAIROSVG = True
except ImportError:
    HAS_CAIROSVG = False


def is_running_in_container():
    """Detect if running inside a container (Docker or Singularity)"""
    # Check environment variable first
    if os.environ.get('IGVER_IN_CONTAINER', '').strip() == '1':
        return True
    if os.environ.get('IGVER_NO_SINGULARITY', '').strip() == '1':
        return True
    
    # Check for Docker
    if os.path.exists('/.dockerenv'):
        return True
    
    # Check for Singularity
    if os.environ.get('SINGULARITY_CONTAINER'):
        return True
    
    # Check cgroup for docker/lxc
    try:
        with open('/proc/1/cgroup', 'r') as f:
            content = f.read()
            if 'docker' in content or 'lxc' in content:
                return True
    except:
        pass
    
    return False


def _get_figures(png_paths, remove_png, dpi, debug):
    figures = []
    for png_path in png_paths:
        image = Image.open(png_path)
        width, height = image.size  # Get original image dimensions

        # Convert to inches for Matplotlib
        figsize = (width / dpi, height / dpi)

        fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
        ax.imshow(image)
        ax.axis("off")

        figures.append(fig)

        # Remove the temp PNG if requested
        if remove_png:
            os.remove(png_path)
            if debug:
                print(f"[LOG:{time.ctime()}] Removed image {png_path}")
    
    return figures


def _convert_svg_to_pdf(svg_paths, remove_svg, dpi, debug):
    """Convert SVG files to PDF format"""
    if not HAS_CAIROSVG:
        raise ImportError("cairosvg is required for PDF output. Install with: pip install cairosvg")
    
    pdf_paths = []
    for svg_path in svg_paths:
        pdf_path = svg_path.replace('.svg', '.pdf')
        
        # Convert SVG to PDF
        cairosvg.svg2pdf(url=svg_path, write_to=pdf_path, dpi=dpi)
        pdf_paths.append(pdf_path)
        
        if debug:
            print(f"[LOG:{time.ctime()}] Converted {svg_path} to {pdf_path}")
        
        # Remove SVG if requested
        if remove_svg:
            os.remove(svg_path)
            if debug:
                print(f"[LOG:{time.ctime()}] Removed SVG file {svg_path}")
    
    return pdf_paths


def load_screenshots(paths, regions, output_dir='/tmp', genome="hg19", igv_dir="/opt/IGV_2.19.8",
                     overwrite=True, remove_png=True, dpi=300,
                     singularity_image='docker://sahuno/igver:latest', singularity_args='-B /home',
                     debug=False, output_format='png', use_singularity=None,
                     load_figures=True, jobs=1, stall_timeout=600, igv_prefs=None, **kwargs):
    """
    Generates IGV screenshots and optionally loads them into Matplotlib figures.

    Parameters:
        paths (list of str): Paths to input files (BAM, BEDPE, VCF, bigWig, etc).
        regions (list of str): List of genomic regions in 'chr:start-end' format.
        output_dir (str, optional): Directory for output screenshots (default: "/tmp").
        genome (str, optional): Genome version (default: "hg19").
        igv_dir (str, optional): Directory containing IGV installation (default: "/opt/IGV_2.19.8").
        overwrite (bool, optional): Whether to overwrite existing PNG files (default: True).
        remove_png (bool, optional): Whether to remove created PNG files (default: True).
        dpi (int, optional): DPI of the figure (default: 300).
        singularity_image (str, optional): singularity image path (default: "docker://sahuno/igver:latest").
        singularity_args (str, optional): singularity arguments string (default: "-B /home").
        debug (bool, optional): Whether to show logs for debugging (default: False).
        output_format (str, optional): Output image format - 'png', 'svg', or 'pdf' (default: 'png').
        load_figures (bool, optional): Whether to load screenshots into Matplotlib figures (default: True).
            Set to False when only file output is needed (e.g. CLI usage) to avoid memory overhead.
        jobs (int, optional): Number of IGV processes to run in parallel. Regions are split into
            `jobs` contiguous chunks, each rendered by its own IGV/JVM (default: 1).
        stall_timeout (int, optional): Kill an IGV process if it produces no new snapshot for this
            many seconds, then retry the missing regions once; 0 disables (default: 600).
        igv_prefs (list of str, optional): Extra 'KEY=VALUE' IGV preferences appended after the bundled
            template in each run's IGV directory (see parse_igv_prefs) (default: None).
        **kwargs (optional): *kwargs* such as tag, max_panel_height, overlap_display, igv_config for create_batch_script

    Returns:
        list: If load_figures=True, returns matplotlib.figure.Figure objects.
              If load_figures=False, returns file paths to the generated screenshots.
    """
    from .igver import create_batch_script, run_igv  # Import helper functions

    # Create batch script and expected PNG paths
    tmpdir = os.getenv("TMPDIR", output_dir)  # Default to /tmp if TMPDIR is not set
    if output_dir == '/tmp':
        output_dir = os.environ.get('TMPDIR', '/tmp')
    if debug:
        print(f"[LOG:{time.ctime()}] TMPDIR is set to: {tmpdir}")
    # Pass output_format to create_batch_script
    batch_script, output_paths = create_batch_script(paths, regions, output_dir, genome, 
                                                     output_format=output_format, **kwargs)
    for path in paths:
        abspath = os.path.abspath(path)
        realpath = os.path.realpath(path)
        bam_dir_abs = os.path.split(abspath)[0]
        bam_dir_real = os.path.split(realpath)[0]
        singularity_args += f' -B {bam_dir_abs}'
        if bam_dir_abs != bam_dir_real:
            singularity_args += f' -B {bam_dir_real}'
    singularity_args += f' -B {os.path.realpath(output_dir)}'
    singularity_args += f' -B {tmpdir}'

    # Run IGV to generate the screenshots
    singularity_image = os.environ.get('IGVER_IMAGE', singularity_image)

    def _run(batch, paths):
        run_igv(batch, paths, igv_dir, overwrite,
            singularity_image=singularity_image, singularity_args=singularity_args,
            debug=debug, use_singularity=use_singularity, stall_timeout=stall_timeout,
            igv_prefs=igv_prefs, run_dir_base=tmpdir)

    if jobs > 1:
        # Split the batch into contiguous region chunks and render each in its own IGV process
        with open(batch_script) as f:
            header, blocks = _split_batch(f.read())
        os.remove(batch_script)
        n_chunks = max(1, min(jobs, len(blocks)))
        size = -(-len(blocks) // n_chunks)  # ceil
        chunks = [blocks[i:i + size] for i in range(0, len(blocks), size)]
        if debug:
            print(f"[LOG:{time.ctime()}] Rendering {len(blocks)} regions in {len(chunks)} parallel IGV processes")

        def _run_chunk(chunk):
            chunk_batch = os.path.join(output_dir, f'{uuid.uuid4()}.batch')
            _write_batch(chunk_batch, header, chunk)
            names = {_snapshot_name(b) for b in chunk}
            _run(chunk_batch, [p for p in output_paths if os.path.basename(p) in names])

        with ThreadPoolExecutor(max_workers=len(chunks)) as pool:
            futures = [pool.submit(_run_chunk, chunk) for chunk in chunks]
        # Report every failed chunk, not only the first: each names its own kept IGV directory
        errors = [f.exception() for f in futures if f.exception() is not None]
        if len(errors) == 1:
            raise errors[0]
        if errors:
            raise RuntimeError(f"{len(errors)} of {len(chunks)} parallel IGV processes failed:\n"
                               + '\n'.join(f'  [{i + 1}] {e}' for i, e in enumerate(errors)))
    else:
        _run(batch_script, output_paths)

    # Check if screenshots were generated
    if not output_paths:
        raise RuntimeError("[ERROR] No screenshots generated.")

    # PDF is rendered by IGV as SVG and converted here, regardless of load_figures
    if output_format == 'pdf':
        output_paths = _convert_svg_to_pdf(output_paths, remove_png, dpi, debug)

    # Only PNG can be loaded into matplotlib; skipping it avoids unclosed-figure memory leaks
    # on large region sets (the CLI always passes load_figures=False).
    if not load_figures or output_format != 'png':
        return output_paths
    return _get_figures(output_paths, remove_png, dpi, debug)


# Locus grammar: the contig is everything before the LAST colon, so hg38 alt contigs such as
# HLA-A*01:01:01:01 stay one contig; coordinates may contain thousands separators.
LOCUS_RE = re.compile(r'^(.+):([0-9][0-9,]*)-([0-9][0-9,]*)$')
UNSAFE_FILENAME_CHARS = re.compile(r'[^A-Za-z0-9._+=,-]')
MAX_FILENAME_BYTES = 200


def parse_locus(token):
    """
    Parse one 'contig:start-end' token.

    Parameters:
        token (str): A whitespace-free token.

    Returns:
        tuple or None: (contig, start, end) with integer coordinates (commas removed), or None if
            the token is not a locus. start > end is returned as is; callers reject it.

    Example:
        >>> parse_locus('HLA-A*01:01:01:01:1-100')
        ('HLA-A*01:01:01:01', 1, 100)
        >>> parse_locus('chr1:1-2.L1.1.+') is None
        True
    """
    m = LOCUS_RE.match(token)
    if not m:
        return None
    return m.group(1), int(m.group(2).replace(',', '')), int(m.group(3).replace(',', ''))


def sanitize_name(name):
    """
    Make a user-derived string safe as part of a snapshot filename.

    Every character outside [A-Za-z0-9._+=,-] becomes '_' (IGV splits batch arguments on
    whitespace, '/' would name a missing subdirectory, and ':' '|' are invalid on Windows/OneDrive),
    runs of '_' collapse to one, and leading '.'/'_' are removed (no hidden files). Idempotent.

    Parameters:
        name (str): BED name, region-file tag or tag argument.

    Returns:
        str: The sanitised name (may be empty).

    Example:
        >>> sanitize_name('chr1:1-2.L1|3.-')
        'chr1_1-2.L1_3.-'
    """
    name = UNSAFE_FILENAME_CHARS.sub('_', name)
    name = re.sub(r'_+', '_', name)
    return name.lstrip('._')


def _snapshot_filename(region_tags, tag, ext):
    """
    Build a snapshot filename '<region>[.<region>...][.<tag>].<ext>' of at most 200 bytes.

    Parameters:
        region_tags (list of str): One 'contig-start-end' string per locus (or a feature name).
        tag (str): Optional label; sanitised, and truncated first when the name is too long.
        ext (str): Extension without the dot.

    Returns:
        str: The filename.

    Example:
        >>> _snapshot_filename(['chr1-100-200'], 'my region', 'png')
        'chr1-100-200.my_region.png'
    """
    region = '.'.join(sanitize_name(t) for t in region_tags)
    tag = sanitize_name(tag or '')
    budget = MAX_FILENAME_BYTES - len(region) - len(ext) - 2
    if tag and budget > 0:
        region += '.' + tag[:budget]
    stem_max = MAX_FILENAME_BYTES - len(ext) - 1
    return f'{region[:stem_max]}.{ext}'


def _region_record(goto, region_tags, tag):
    """A parsed region: the `goto` argument plus the parts of its snapshot filename."""
    return {'goto': goto, 'region_tags': region_tags, 'tag': tag}


def _open_text(path):
    """Open a text file, transparently gunzipping '*.gz'."""
    if path.lower().endswith('.gz'):
        return gzip.open(path, 'rt')
    return open(path)


def _bed_line_record(path, n, fields, tag):
    """Turn BED fields into a region record; BED is 0-based half-open, IGV's goto is 1-based closed."""
    chrom, start, end = fields[0].strip(), fields[1].strip(), fields[2].strip()
    if not (start.isdigit() and end.isdigit()):
        raise ValueError(f"{path}:{n}: BED start/end must be integers, got '{start}' and '{end}'")
    start, end = int(start), int(end)
    if end < start:
        raise ValueError(f"{path}:{n}: BED end {end} is before start {start}")
    name = fields[3].strip() if len(fields) > 3 else ''
    # The filename keeps the BED coordinates (downstream scripts match on them)
    return _region_record(f'{chrom}:{start + 1}-{max(end, start + 1)}', [f'{chrom}-{start}-{end}'],
                          name or tag)


def _bed_records(bed_file, tag=None):
    """
    Parse a BED file (BED3+, optionally gzipped) into region records.

    Tab-separated fields are expected; a line with fewer than 3 tab fields but at least 3
    whitespace fields is read on whitespace (one warning per file). `#`, `track` and `browser`
    lines are skipped. Any other unparseable line, or a file without regions, is an error.

    Parameters:
        bed_file (str): Path to a .bed or .bed.gz file.
        tag (str, optional): Label for records without a name column (default: None).

    Returns:
        list of dict: Region records (see _region_record).

    Raises:
        ValueError: With '<file>:<line>' for a bad line, or '<file>' when it holds no regions.

    Example:
        >>> _bed_records('r.hg19.bed')[0]['goto']  # file: "chr1<TAB>100<TAB>200"
        'chr1:101-200'
    """
    records, warned = [], False
    with _open_text(bed_file) as f:
        for n, raw in enumerate(f, 1):
            line = raw.rstrip('\r\n')
            stripped = line.strip()
            if not stripped or stripped.startswith(('#', 'track', 'browser')):
                continue
            fields = line.split('\t')
            if len(fields) < 3:
                fields = stripped.split()
                if len(fields) < 3:
                    raise ValueError(f"{bed_file}:{n}: expected at least 3 tab-separated fields "
                                     f"(chrom, start, end): '{stripped}'")
                if not warned:
                    print(f"[WARNING] {bed_file} is whitespace-separated, not tab-separated; "
                          f"reading it on whitespace (a name with spaces keeps only its first word)")
                    warned = True
            records.append(_bed_line_record(bed_file, n, fields, tag))
    if not records:
        raise ValueError(f"{bed_file}: no regions found (empty, or only header/comment lines)")
    return records


def _text_records(region_file, tag=None):
    """
    Parse a text region file into region records.

    Grammar (per line, whitespace-separated tokens): the LEADING tokens that are loci
    (contig:start-end) are shown together (several = IGV split view, e.g. for SVs); everything from
    the first non-locus token on is the tag, joined with '_'. A line without a leading locus is read
    as BED if it looks like BED (>= 3 fields, fields 2-3 integers; warned once per file), and is
    an error otherwise. '#' lines and blank lines are skipped.

    Parameters:
        region_file (str): Path to the text file.
        tag (str, optional): Label for lines without their own tag (default: None).

    Returns:
        list of dict: Region records (see _region_record).

    Raises:
        ValueError: '<file>:<line>: ...' for a line without a locus or with start > end.

    Example:
        >>> _text_records('sv.txt')[0]  # file: "8:1-2 19:3-4 translocation"
        {'goto': '8:1-2 19:3-4', 'region_tags': ['8-1-2', '19-3-4'], 'tag': 'translocation'}
    """
    records, warned = [], False
    with _open_text(region_file) as f:
        for n, raw in enumerate(f, 1):
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            tokens = line.split()
            loci = []
            for token in tokens:
                locus = parse_locus(token)
                if locus is None:
                    break
                loci.append(locus)
            if loci:
                for contig, start, end in loci:
                    if start > end:
                        raise ValueError(f"{region_file}:{n}: start {start} > end {end} in "
                                         f"'{contig}:{start}-{end}'")
                records.append(_region_record(
                    ' '.join(f'{c}:{s}-{e}' for c, s, e in loci),
                    [f'{c}-{s}-{e}' for c, s, e in loci],
                    '_'.join(tokens[len(loci):]) or tag))
            elif len(tokens) >= 3 and tokens[1].isdigit() and tokens[2].isdigit():
                if not warned:
                    print(f"[WARNING] BED-like lines in {region_file} are read as BED (0-based start); "
                          f"consider a .bed extension")
                    warned = True
                # tab fields keep a name with spaces; a stray tab that breaks the columns falls back
                fields = line.split('\t')
                if len(fields) < 3 or not (fields[1].strip().isdigit() and fields[2].strip().isdigit()):
                    fields = tokens
                records.append(_bed_line_record(region_file, n, fields, tag))
            else:
                raise ValueError(f"{region_file}:{n}: line does not start with a chr:start-end locus "
                                 f"and is not a BED record: '{line}'")
    return records


def _string_records(region, tag=None):
    """
    Turn a -r region argument (not a file) into a region record.

    Parameters:
        region (str): 'chr:start-end', several loci separated by spaces (split view), or a feature
            name for IGV's search (e.g. a gene).
        tag (str, optional): Label appended to the filename (default: None).

    Returns:
        list of dict: One region record.

    Example:
        >>> _string_records('chr1:1-100 chr2:5-10')[0]['goto']
        'chr1:1-100 chr2:5-10'
    """
    tokens = region.split()
    loci = [parse_locus(t) for t in tokens]
    if tokens and all(loci):
        return [_region_record(' '.join(f'{c}:{s}-{e}' for c, s, e in loci),
                               [f'{c}-{s}-{e}' for c, s, e in loci], tag)]
    return [_region_record(region, [region.replace(':', '-').replace(' ', '.')], tag)]


def _records_to_batch(records, output_dir, overlap_display='squish', max_panel_height=200,
                      additional_pref=None, output_format='png'):
    """
    Turn region records into snapshot paths and batch lines.

    Parameters:
        records (list of dict): Region records.
        output_dir (str): Snapshot directory.
        overlap_display (str): Display commands emitted per region ('' or 'expand' = none).
        max_panel_height (int): maxPanelHeight per region.
        additional_pref (str): Extra batch commands before each snapshot.
        output_format (str): 'png', 'svg' or 'pdf' (pdf is written by IGV as svg).

    Returns:
        (list of str, list of str): Snapshot paths and batch lines.

    Example:
        >>> _records_to_batch([_region_record('chr1:1-2', ['chr1-1-2'], None)], '/out')[0]
        ['/out/chr1-1-2.png']
    """
    ext = 'svg' if output_format in ['svg', 'pdf'] else output_format
    png_paths, region_content = [], []
    for rec in records:
        png_fname = _snapshot_filename(rec['region_tags'], rec['tag'], ext)
        png_paths.append(os.path.join(output_dir, png_fname))
        region_content.append(f"goto {rec['goto']}")
        if overlap_display and overlap_display != 'expand':
            region_content.append(overlap_display)
        region_content.append(f'maxPanelHeight {max_panel_height}')
        if additional_pref:
            region_content.append(additional_pref)
        region_content.append(f'snapshot {png_fname}')
    return png_paths, region_content


def _parse_bed_file(bed_file, output_dir, overlap_display='squish', max_panel_height=200, additional_pref=None, tag=None, output_format='png'):
    """
    Parse a BED file (BED3/BED6, tab- or whitespace-separated, optionally gzipped) into snapshots.

    BED starts are 0-based: `chr1 100 200` becomes `goto chr1:101-200` with the filename
    `chr1-100-200[.<name>].png`. The name column (4th field) is sanitised (see sanitize_name).

    Returns:
        (list of str, list of str): Snapshot paths and batch lines.
    """
    return _records_to_batch(_bed_records(bed_file, tag), output_dir, overlap_display,
                             max_panel_height, additional_pref, output_format)


def _parse_region_file(region_file, output_dir, overlap_display='squish', max_panel_height=200, additional_pref=None, tag=None, output_format='png'):
    """
    Parse a text region file (see _text_records for the grammar) into snapshots.

    Returns:
        (list of str, list of str): Snapshot paths and batch lines.
    """
    return _records_to_batch(_text_records(region_file, tag), output_dir, overlap_display,
                             max_panel_height, additional_pref, output_format)


def _parse_region_string(region, output_dir, overlap_display='squish', max_panel_height=200, additional_pref=None, tag=None, output_format='png'):
    """
    Parse a -r region argument (see _string_records) into a snapshot.

    Returns:
        (list of str, list of str): Snapshot path and batch lines.
    """
    return _records_to_batch(_string_records(region, tag), output_dir, overlap_display,
                             max_panel_height, additional_pref, output_format)


ALIGNMENT_EXTENSIONS = ('.bam', '.cram', '.sam')


def _display_commands(paths, overlap_display):
    """
    Build the batch commands that apply ``overlap_display`` to alignment tracks only.

    A bare ``squish``/``expand`` applies to every track, and a squished or expanded annotation
    track (the genome's RefSeq track, BED files) grows to fill the panel and pushes the tracks
    below it out of the snapshot. Naming each alignment track keeps annotation tracks in IGV's
    default layout. 'expand' is IGV's default for reads, so it emits nothing.

    Parameters:
        paths (list of str): Track paths as passed to ``load``.
        overlap_display (str): 'expand', 'collapse' or 'squish'.

    Returns:
        str: Newline-joined commands, or '' when there is nothing to emit.

    Example:
        >>> _display_commands(['/data/a.bam', '/data/genes.bed'], 'squish')
        'squish a.bam'
    """
    if overlap_display == 'expand':
        return ''
    names = []
    for path in paths:
        name = os.path.basename(path)
        if not name.lower().endswith(ALIGNMENT_EXTENSIONS) or name in names:
            continue
        if any(c.isspace() for c in name):
            # IGV splits batch arguments on whitespace, so this track cannot be targeted by name
            print(f"[WARNING] '{name}' contains whitespace; -d {overlap_display} is not applied to it")
            continue
        names.append(name)
    return '\n'.join(f'{overlap_display} {name}' for name in names)


def create_batch_script(paths, regions, output_dir, genome='hg19', tag=None, max_panel_height=200,
                        overlap_display='squish', igv_config=None, color_by=None, output_format='png'):
    """
    Creates an IGV batch script to generate screenshots for the given BAM files and regions.

    Parameters:
        paths (list of str): Paths to BAM files.
        regions (list of str): List of regions in 'chr:start-end' format.
        output_dir (str): Directory where screenshots will be saved.
        genome (str, optional): Genome version (default: 'hg19').
        tag (str, optional): Tag to suffix the PNG file name (default: None).
        max_panel_height (int, optional): Maximum panel height for IGV (default: 200).
        overlap_display (str, optional): Display mode for overlapping reads ('expand', 'collapse', 'squish',
            default: 'squish'). Applied to alignment tracks (BAM/CRAM/SAM) by name only; annotation
            tracks keep IGV's default layout.
        igv_config (str, optional): Path to file containing IGV batch commands to inject before
            each snapshot (default: None). Must use IGV batch command syntax (e.g. 'colorBy BASE_MODIFICATION'),
            not KEY=VALUE properties format.
        color_by (str, optional): IGV colorBy value injected before each snapshot (e.g. 'BASE_MODIFICATION',
            'TAG HP'). Emitted before igv_config commands (default: None).

    Returns:
        str: The path to the generated IGV batch script.
    """
    assert overlap_display in ['expand', 'collapse', 'squish'], f"Invalid overlap_display: {overlap_display}"

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Generate a unique batch file name
    batch_filename = os.path.join(output_dir, f'{uuid.uuid4()}.batch')

    # Build additional_pref: color_by first, then igv_config commands
    additional_pref_parts = []

    if color_by:
        additional_pref_parts.append(f'colorBy {color_by}')

    if igv_config and os.path.exists(igv_config):
        with open(igv_config, 'r') as f:
            config_content = f.read().strip()
        # Warn if any lines look like KEY=VALUE properties format (silently ignored by IGV batch interpreter)
        for line in config_content.splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line and not line.startswith('preference'):
                print(f"[WARNING] igv-config line looks like properties format: '{line}'")
                print(f"  IGV batch scripts do not support KEY=VALUE syntax. Use batch command syntax instead:")
                print(f"  e.g. 'preference {line.replace('=', ' ')}' or 'colorBy BASE_MODIFICATION'")
                break  # Warn once, not per line
        additional_pref_parts.append(config_content)

    additional_pref = '\n'.join(additional_pref_parts)

    # Create batch file content
    # Absolute paths: IGV resolves relative paths against the batch file's directory, and inside
    # a container the working directory may not be the caller's.
    batch_content = [
        'new',
        f'snapshotDirectory {os.path.abspath(output_dir)}',
        f'genome {genome}'
    ]
    for bam in paths:
        batch_content.append(f'load {os.path.abspath(bam)}')
    
    png_paths, region_content = _get_paths_and_regions(regions,
        output_dir=output_dir, overlap_display=_display_commands(paths, overlap_display),
        max_panel_height=max_panel_height, additional_pref=additional_pref, tag=tag,
        output_format=output_format)
    batch_content += region_content
    batch_content.append('exit')
    batch_text = '\n'.join(batch_content)
    
    # Write to batch file
    with open(batch_filename, 'w') as batch_file:
        batch_file.write(batch_text)
    
    return batch_filename, png_paths


def _get_paths_and_regions(regions, output_dir, tag=None, **kwargs):
    """
    Parse every -r argument (BED file, text region file, or region string) into snapshots.

    Parameters:
        regions (list of str): Region arguments, in order.
        output_dir (str): Snapshot directory.
        tag (str, optional): Label for regions without their own name/tag (default: None).
        **kwargs: overlap_display, max_panel_height, additional_pref, output_format
            (see _records_to_batch).

    Returns:
        (list of str, list of str): Snapshot paths and batch lines.

    Example:
        >>> _get_paths_and_regions(['chr1:1-2'], output_dir='/out')[0]
        ['/out/chr1-1-2.png']
    """
    records = []
    for region in regions:
        if os.path.isfile(region):
            if region.lower().endswith(('.bed', '.bed.gz')):
                records += _bed_records(region, tag)
            else:
                records += _text_records(region, tag)
        else:
            records += _string_records(region, tag)
    return _records_to_batch(records, output_dir, **kwargs)


def _remove_previous_output(png_paths, debug=False):
    for png_path in png_paths:
        if os.path.exists(png_path):
            os.remove(png_path)
            if debug:
                print(f"[LOG:{time.ctime()}] Removed existing {png_path}")


def _split_batch(batch_text):
    """
    Split IGV batch text into its header and per-region blocks.

    Parameters:
        batch_text (str): Contents of a batch file written by create_batch_script.

    Returns:
        tuple: (header_lines, blocks) where header_lines is the list of lines before the first
            `goto` (new/snapshotDirectory/genome/load ...) and blocks is a list of line-lists, one
            per region, each starting at `goto` and ending at `snapshot`. The trailing `exit` is dropped.

    Example:
        >>> header, blocks = _split_batch("new\ngenome hg19\ngoto chr1:1-2\nsnapshot a.png\nexit")
        >>> header, blocks
        (['new', 'genome hg19'], [['goto chr1:1-2', 'snapshot a.png']])
    """
    lines = [line for line in batch_text.splitlines() if line.strip() != 'exit']
    first = next((i for i, line in enumerate(lines) if line.startswith('goto ')), len(lines))
    header, blocks = lines[:first], []
    for line in lines[first:]:
        if line.startswith('goto '):
            blocks.append([])
        blocks[-1].append(line)
    return header, blocks


def _write_batch(path, header, blocks):
    """Write header + region blocks + exit as an IGV batch file at `path`."""
    with open(path, 'w') as f:
        f.write('\n'.join(header + [line for block in blocks for line in block] + ['exit']))


def _snapshot_name(block):
    """Return the snapshot filename a region block writes (its final `snapshot <name>` line)."""
    return block[-1][len('snapshot '):].strip()


def _run_until_stalled(cmd, png_paths, stall_timeout, debug=False):
    """
    Run an IGV command, killing its whole process group if it stops producing snapshots.

    IGV in batch mode turns any uncaught error (unreachable annotation server, unloadable
    track, ...) into a modal dialog on the virtual display and then waits forever for a click.
    Zero progress is the only external symptom, so progress is what we watch.

    Parameters:
        cmd (str): Shell command that launches IGV.
        png_paths (list of str): Expected snapshot paths; progress = number that exist.
        stall_timeout (int): Seconds without a new snapshot before IGV is killed. 0 disables.
        debug (bool, optional): Print IGV stdout/stderr (default: False).

    Returns:
        bool: True if IGV exited on its own, False if it was killed for stalling.

    Example:
        >>> _run_until_stalled('sleep 60', ['/nonexistent.png'], stall_timeout=1)
        False
    """
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            start_new_session=True)
    n_done = sum(os.path.exists(p) for p in png_paths)
    last_progress = time.time()
    finished = True
    while True:
        try:
            stdout, stderr = proc.communicate(timeout=5)
            break
        except subprocess.TimeoutExpired:
            pass
        n_now = sum(os.path.exists(p) for p in png_paths)
        if n_now > n_done:
            n_done, last_progress = n_now, time.time()
        elif stall_timeout and time.time() - last_progress > stall_timeout:
            os.killpg(proc.pid, signal.SIGTERM)  # let xvfb-run remove its display lock
            try:
                stdout, stderr = proc.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                stdout, stderr = proc.communicate()
            finished = False
            print(f"[WARNING:{time.ctime()}] IGV produced no new snapshot for {stall_timeout}s "
                  f"({n_done}/{len(png_paths)} done); killed. This usually means IGV hit an error "
                  f"and is blocked on a dialog.", file=sys.stderr)
            break
    if debug:
        print(f"[STDOUT:{time.ctime()}]\n{stdout.decode()}")
        print(f"[STDERR:{time.ctime()}]\n{stderr.decode()}")
    return finished


PREFS_TEMPLATE = 'igv_prefs.properties'


def read_prefs_template():
    """
    Return the bundled IGV preferences template (igver/data/igv_prefs.properties).

    Returns:
        str: The template text (KEY=VALUE lines and comments).

    Example:
        >>> 'PORT_ENABLED=false' in read_prefs_template()
        True
    """
    return resources.files('igver.data').joinpath(PREFS_TEMPLATE).read_text()


def parse_igv_prefs(path):
    """
    Read a user IGV preferences file for --igv-prefs.

    Blank lines and '#' comments are skipped; every other line must be KEY=VALUE with a non-empty,
    whitespace-free key. Whitespace around the key and value is removed.

    Parameters:
        path (str): Path to the preferences file.

    Returns:
        list of str: Normalised 'KEY=VALUE' lines, in file order (may be empty).

    Raises:
        FileNotFoundError: The file does not exist.
        ValueError: A line is not KEY=VALUE; the message starts with '<path>:<line number>'.

    Example:
        >>> parse_igv_prefs('my.prefs')  # file: "SAM.SHOW_SOFT_CLIPPED = true"
        ['SAM.SHOW_SOFT_CLIPPED=true']
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"--igv-prefs file not found: {path}")
    lines = []
    with open(path) as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            key, sep, value = line.partition('=')
            key, value = key.strip(), value.strip()
            if not sep or not key or any(c.isspace() for c in key):
                raise ValueError(f"{path}:{n}: not a KEY=VALUE preference line: '{line}'")
            lines.append(f'{key}={value}')
    return lines


def _batch_genome(batch_script):
    """Return the argument of the batch file's `genome` line, or None."""
    with open(batch_script) as f:
        for line in f:
            if line.startswith('genome '):
                return line[len('genome '):].strip().strip('"')
    return None


def _make_igv_run_dir(base, genome=None, igv_prefs=None):
    """
    Create a fresh, run-scoped IGV directory holding igver's preferences.

    IGV keeps a prefs.properties it finds in --igvDirectory; without one it copies the user's
    ~/igv/prefs.properties in, so the file is always written here.

    Parameters:
        base (str): Parent directory (must be visible inside the container).
        genome (str, optional): Written as DEFAULT_GENOME_KEY, so IGV loads only this genome at
            startup instead of its default genome first (default: None).
        igv_prefs (list of str, optional): Extra 'KEY=VALUE' lines appended last (default: None).

    Returns:
        str: Path of the new directory (prefix 'igver_igv_').

    Example:
        >>> d = _make_igv_run_dir('/tmp', genome='hg19')
        >>> 'DEFAULT_GENOME_KEY=hg19' in open(os.path.join(d, 'prefs.properties')).read()
        True
    """
    os.makedirs(base, exist_ok=True)
    run_dir = tempfile.mkdtemp(prefix='igver_igv_', dir=base)
    lines = [read_prefs_template().rstrip('\n'), '', '# written by igver for this run']
    if genome:
        lines.append(f'DEFAULT_GENOME_KEY={genome}')
    if igv_prefs:
        lines += ['# --igv-prefs'] + list(igv_prefs)
    with open(os.path.join(run_dir, 'prefs.properties'), 'w') as f:
        f.write('\n'.join(lines) + '\n')
    return run_dir


def _igv_log_excerpt(run_dir, n_lines=20):
    """
    Return the last `n_lines` SEVERE/ERROR lines of a run directory's IGV log.

    Parameters:
        run_dir (str): IGV directory of the run.
        n_lines (int, optional): Maximum number of lines (default: 20).

    Returns:
        str: The lines joined by newlines, or a note that the log is missing or has no errors.

    Example:
        >>> _igv_log_excerpt('/tmp/igver_igv_x')
        'SEVERE [..] [TrackLoader] Error loading /data/x.bam ...'
    """
    log = os.path.join(run_dir, 'igv0.log')
    if not os.path.exists(log):
        return f'(no IGV log at {log})'
    with open(log, errors='replace') as f:
        hits = [line.rstrip() for line in f if line.startswith(('SEVERE', 'ERROR'))]
    return '\n'.join(hits[-n_lines:]) if hits else f'(no SEVERE/ERROR lines in {log})'


def run_igv(batch_script, png_paths, igv_dir="/opt/IGV_2.19.8", overwrite=False, 
            singularity_image='docker://sahuno/igver:latest', singularity_args='-B /data1 -B /home',
            debug=False, use_singularity=None, stall_timeout=600, igv_prefs=None,
            run_dir_base=None):
    """
    Runs IGV using the generated batch script and ensures all PNG screenshots are created.

    Every IGV launch gets a fresh IGV directory (``--igvDirectory``) with igver's preferences, so
    the user's ~/igv never affects the output. It is deleted on success and kept on failure, and
    its log excerpt goes into the error message.

    Parameters:
        batch_script (str): Path to the IGV batch script.
        png_paths (list of str): Expected paths of the output PNG screenshot.
        igv_dir (str, optional): Directory containing IGV installation (default: "/opt/IGV_2.19.8").
        overwrite (bool, optional): Whether to overwrite existing PNG files (default: False).
        debug (bool, optional): Whether to show logs for debugging (default: False).
        stall_timeout (int, optional): Kill IGV if no new snapshot appears for this many seconds;
            0 disables (default: 600). Guards against IGV blocking on an error dialog.
        igv_prefs (list of str, optional): Extra 'KEY=VALUE' preferences for the run (default: None).
        run_dir_base (str, optional): Where run IGV directories are created; must be visible inside
            the container (default: $TMPDIR, else the batch script's directory).

    Returns:
        list of str: Paths to the generated PNG files.
    """
    # Auto-detect if we should use singularity
    if use_singularity is None:
        use_singularity = not is_running_in_container()
    
    # assert os.path.exists(igv_dir), f"[ERROR:{time.ctime()}] {igv_dir} does not exist"
    igv_runfile = os.path.join(igv_dir, "igv.sh")
    # assert os.path.exists(igv_runfile), f"[ERROR:{time.ctime()}] {igv_runfile} does not exist"

    if run_dir_base is None:
        run_dir_base = os.environ.get('TMPDIR') or os.path.dirname(os.path.abspath(batch_script))
    genome = _batch_genome(batch_script)

    def _command(run_dir):
        # igv_dir is the IGV install; run_dir is IGV's writable prefs/cache/log directory
        cmd = (f'xvfb-run --auto-display --server-args="-screen 0 1920x1080x24" {igv_runfile} '
               f'-b {batch_script} --igvDirectory {run_dir}')
        if use_singularity:
            cmd = f'singularity run {singularity_args} {singularity_image} {cmd}'
        return cmd

    if debug:
        mode = 'with Singularity' if use_singularity else 'directly (container mode)'
        print(f"[LOG:{time.ctime()}] Running IGV {mode}")
        with open(batch_script) as f:
            print(f"[LOG:{time.ctime()}] Batch script {batch_script}:\n{f.read()}")

    # If overwrite is enabled, remove existing PNG files
    if overwrite:
        _remove_previous_output(png_paths, debug)

    # Run IGV; on retry, rewrite the batch to cover only the regions still missing
    max_iter = 2
    run_dir = None
    for n_iter in range(max_iter):
        missing = [png for png in png_paths if not os.path.exists(png)]
        if not missing:
            break
        if n_iter > 0:
            with open(batch_script) as f:
                header, blocks = _split_batch(f.read())
            want = {os.path.basename(png) for png in missing}
            _write_batch(batch_script, header, [b for b in blocks if _snapshot_name(b) in want])
            print(f"[WARNING:{time.ctime()}] {len(missing)} snapshot(s) missing; IGV log errors from "
                  f"{run_dir}:\n{_igv_log_excerpt(run_dir)}", file=sys.stderr)
            shutil.rmtree(run_dir, ignore_errors=True)  # the retry gets its own directory
        run_dir = _make_igv_run_dir(run_dir_base, genome=genome, igv_prefs=igv_prefs)
        cmd = _command(run_dir)
        if debug:
            print(f"[LOG:{time.ctime()}] Iteration #{n_iter + 1}: rendering {len(missing)} missing snapshot(s); "
                  f"IGV directory {run_dir}")
            print(f"[LOG:{time.ctime()}] Running IGV command:\n{cmd}")
        _run_until_stalled(cmd, png_paths, stall_timeout, debug)

    if not all(os.path.exists(png) for png in png_paths):
        raise RuntimeError(f"[ERROR:{time.ctime()}] Failed to generate all PNG files after {max_iter} iterations. "
                           f"Batch for the missing regions kept at {batch_script}; IGV directory kept at "
                           f"{run_dir} . Last IGV log errors:\n{_igv_log_excerpt(run_dir)}")
    if run_dir:
        shutil.rmtree(run_dir, ignore_errors=True)

    # Cleanup batch script
    os.remove(batch_script)
    if debug:
        print(f"[LOG:{time.ctime()}] Removed batch script {batch_script}")

    return png_paths
