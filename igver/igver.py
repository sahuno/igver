import os
import signal
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
import uuid
import time

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
                     load_figures=True, jobs=1, stall_timeout=600, **kwargs):
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
            debug=debug, use_singularity=use_singularity, stall_timeout=stall_timeout)

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
            list(pool.map(_run_chunk, chunks))  # list() re-raises worker exceptions
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


def _parse_bed_file(bed_file, output_dir, overlap_display='squish', max_panel_height=200, additional_pref=None, tag=None, output_format='png'):
    """
    Parse BED format file (BED3 or BED6) to extract regions
    BED3: chrom, chromStart, chromEnd
    BED6: chrom, chromStart, chromEnd, name, score, strand
    """
    png_paths = []
    region_content = []
    
    with open(bed_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('track') or line.startswith('browser'):
                continue
                
            fields = line.split('\t')
            if len(fields) < 3:
                continue
                
            chrom = fields[0]
            start = fields[1]
            end = fields[2]
            
            # Handle optional name field from BED6
            region_name = ''
            if len(fields) >= 4 and fields[3]:
                region_name = fields[3]
            
            # Format region string
            region = f"{chrom}:{start}-{end}"
            region_tag = region.replace(':', '-')
            
            # Create filename with appropriate extension
            ext = 'svg' if output_format in ['svg', 'pdf'] else output_format
            if region_name:
                png_fname = f"{region_tag}.{region_name}.{ext}"
            elif tag:
                png_fname = f"{region_tag}.{tag}.{ext}"
            else:
                png_fname = f"{region_tag}.{ext}"
                
            png_path = os.path.join(output_dir, png_fname)
            png_paths.append(png_path)
            
            # Create batch content
            region_content.append(f'goto {region}')
            if overlap_display and overlap_display != 'expand':
                region_content.append(overlap_display)
            region_content.append(f'maxPanelHeight {max_panel_height}')
            if additional_pref:
                region_content.append(additional_pref)
            region_content.append(f'snapshot {png_fname}')
    
    return png_paths, region_content


def _parse_region_file(region_file, output_dir, overlap_display='squish', max_panel_height=200, additional_pref=None, tag=None, output_format='png'):
    """
    Parse region and tag from line (legacy text format)
    """
    png_paths = []
    region_content = []
    for line in open(region_file):
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        out_tag = ''
        sv_tag = ''
        field = line.strip().split() # split by either ' ' or '\t'
        region = []
        region_tags = []
        for item in field:
            is_region = (item.count(':')==1 and item.count('-')==1)
            if is_region:
                region_tag = item.replace(':', '-')
                region_tags.append(region_tag)
                region.append(item)
            else:
                sv_tag = item
        out_tag = '.'.join(region_tags)
        region = ' '.join(region)
        if sv_tag:
            out_tag += f'.{sv_tag}' # e.g. ins, del, translocation, ...
        ext = 'svg' if output_format in ['svg', 'pdf'] else output_format
        png_fname = out_tag + f'.{ext}'
        png_path = os.path.join(output_dir, png_fname)
        png_paths.append(png_path)
        
        region_content.append(f'goto {region}')
        if overlap_display and overlap_display != 'expand':
            region_content.append(overlap_display)
        region_content.append(f'maxPanelHeight {max_panel_height}')
        if additional_pref:
            region_content.append(additional_pref)
        region_content.append(f'snapshot {png_fname}')

    return png_paths, region_content


def _parse_region_string(region, output_dir, overlap_display='squish', max_panel_height=200, additional_pref=None, tag=None, output_format='png'):
    """
    Parse region and tag from cli argument
    """
    region_content = []
    region_tag = region.replace(':', '-').replace(' ', '.')
    ext = 'svg' if output_format in ['svg', 'pdf'] else output_format
    png_fname = f"{region_tag}.{ext}"
    if tag:
        png_fname = f"{region_tag}.{tag}.{ext}"
    png_path = os.path.join(output_dir, png_fname)
    
    region_content.append(f'goto {region}')
    if overlap_display and overlap_display != 'expand':
        region_content.append(overlap_display)
    region_content.append(f'maxPanelHeight {max_panel_height}')
    if additional_pref:
        region_content.append(additional_pref)
    region_content.append(f'snapshot {png_fname}')

    png_paths = [png_path]

    return png_paths, region_content


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


def _get_paths_and_regions(regions, **kwargs):
    png_paths = []
    region_content = []
    for region in regions:
        if os.path.exists(region): # input is region file
            # Check if it's a BED file based on extension
            if region.endswith('.bed'):
                _png_paths, _region_content = _parse_bed_file(region, **kwargs)
            else:
                # Assume it's a text file with custom format
                _png_paths, _region_content = _parse_region_file(region, **kwargs)

        else: # input is region argument(s)
            _png_paths, _region_content = _parse_region_string(region, **kwargs)
        png_paths += _png_paths
        region_content += _region_content
    
    return png_paths, region_content


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
                  f"and is blocked on a dialog. Check ~/igv/igv0.log.", file=sys.stderr)
            break
    if debug:
        print(f"[STDOUT:{time.ctime()}]\n{stdout.decode()}")
        print(f"[STDERR:{time.ctime()}]\n{stderr.decode()}")
    return finished


def run_igv(batch_script, png_paths, igv_dir="/opt/IGV_2.19.8", overwrite=False, 
            singularity_image='docker://sahuno/igver:latest', singularity_args='-B /data1 -B /home',
            debug=False, use_singularity=None, stall_timeout=600):
    """
    Runs IGV using the generated batch script and ensures all PNG screenshots are created.

    Parameters:
        batch_script (str): Path to the IGV batch script.
        png_paths (list of str): Expected paths of the output PNG screenshot.
        igv_dir (str, optional): Directory containing IGV installation (default: "/opt/IGV_2.19.8").
        overwrite (bool, optional): Whether to overwrite existing PNG files (default: False).
        debug (bool, optional): Whether to show logs for debugging (default: False).
        stall_timeout (int, optional): Kill IGV if no new snapshot appears for this many seconds;
            0 disables (default: 600). Guards against IGV blocking on an error dialog.

    Returns:
        list of str: Paths to the generated PNG files.
    """
    # Auto-detect if we should use singularity
    if use_singularity is None:
        use_singularity = not is_running_in_container()
    
    # assert os.path.exists(igv_dir), f"[ERROR:{time.ctime()}] {igv_dir} does not exist"
    igv_runfile = os.path.join(igv_dir, "igv.sh")
    # assert os.path.exists(igv_runfile), f"[ERROR:{time.ctime()}] {igv_runfile} does not exist"

    # IGV command
    cmd = f'xvfb-run --auto-display --server-args="-screen 0 1920x1080x24" {igv_runfile} -b {batch_script} --igvDirectory {igv_dir}'
    
    # Only wrap with singularity if needed
    if use_singularity:
        cmd = f'singularity run {singularity_args} {singularity_image} {cmd}'
        if debug:
            print(f"[LOG:{time.ctime()}] Running IGV with Singularity")
    else:
        if debug:
            print(f"[LOG:{time.ctime()}] Running IGV directly (container mode)")
    
    if debug:
        print(f"[LOG:{time.ctime()}] Running IGV command:\n{cmd}")

    # If overwrite is enabled, remove existing PNG files
    if overwrite:
        _remove_previous_output(png_paths, debug)

    # Run IGV; on retry, rewrite the batch to cover only the regions still missing
    max_iter = 2
    for n_iter in range(max_iter):
        missing = [png for png in png_paths if not os.path.exists(png)]
        if not missing:
            break
        if n_iter > 0:
            with open(batch_script) as f:
                header, blocks = _split_batch(f.read())
            want = {os.path.basename(png) for png in missing}
            _write_batch(batch_script, header, [b for b in blocks if _snapshot_name(b) in want])
        if debug:
            print(f"[LOG:{time.ctime()}] Iteration #{n_iter + 1}: rendering {len(missing)} missing snapshot(s)")
        _run_until_stalled(cmd, png_paths, stall_timeout, debug)

    if not all(os.path.exists(png) for png in png_paths):
        raise RuntimeError(f"[ERROR:{time.ctime()}] Failed to generate all PNG files after {max_iter} iterations. "
                           f"Batch for the missing regions kept at {batch_script}; see ~/igv/igv0.log for IGV errors.")

    # Cleanup batch script
    os.remove(batch_script)
    if debug:
        print(f"[LOG:{time.ctime()}] Removed batch script {batch_script}")

    return png_paths
