# Shoot IGV
Conveniently take IGV snapshots in multiple bam files over mutliple regions 

# Prerequisites
The standard say of running `shoot_igv.py` is through singularity. But if you have `xvfb-run` installed you can use it as is.
You need to have a `$HOME/igv` directory with `genomes/hg19.genome` for hg19 or some other genome of your choosing inside it.

# Usage
```bash
usage: shoot_igv.py [-h] --bam BAM [BAM ...] -r REGIONS -o OUTDIR [-t TAG]
                    [-mph MAX_PANEL_HEIGHT] [-od OVERLAP_DISPLAY]
                    [--overwrite OVERWRITE] [--config CONFIG]

Create temporary batchfile and run IGV for a region list

optional arguments:
  -h, --help            show this help message and exit
  --bam BAM [BAM ...]   Input tumor bam file(s) to be shown vertically
  -r REGIONS, --regions REGIONS
                        Either 'chr:start-end' string, or input regions file
                        with region columns to be shown horizontally
  -o OUTDIR, --outdir OUTDIR
                        Output png directory
  -t TAG, --tag TAG     Tag to suffix your png file [default: 'tumor']
  -mph MAX_PANEL_HEIGHT, --max_panel_height MAX_PANEL_HEIGHT
                        Max panel height [default: 200]
  -od OVERLAP_DISPLAY, --overlap_display OVERLAP_DISPLAY
                        'expand', 'collapse' or 'squish'; [default: 'squish']
  --overwrite OVERWRITE
                        Overwrite existing png files [default: False]
  --config CONFIG       Additional preferences [default: None]
```

## Additinoal IGV preferences
You can plug in additional IGV preferences as in https://github.com/igvteam/igv/wiki/Batch-commands -- an example would be `test/tag_haplotype.batch`:
```
group TAG HP
colorBy TAG rl
sort READNAME
```

# Run example
An example command getting two bam files as input, to be displayed vertically in the order put in (i.e. top panel: `haplotag_tumor.bam`, bottom panel: `haplotag_normal.bam`).
`test/tag_haplotype.batch` includes additional IGV preferences to group and color haplotagged reads.
```bash
singularity run -B /juno docker://shahcompbio/igv ./shoot_igv.py \
    --bam test/test_tumor.bam test/test_normal.bam \
    -r test/region.txt \
    -o test/snapshots \
    -mph 500 -od squish \
    --config test/tag_haplotype.batch
```
1. The first region will take a 1001bp snapshot on the region coined "region of interest", and create a png file `1-122535169-112537169.region_of_interest.tumor.png` in the OUTDIR.
2. The second region will take a 1001bp snapshot on the two breakpoints of the translocation, and create a png file `8-32534767-32536767.19-11137898-11139898.translocation.tumor.png` in the OUTDIR.
3. The third region will take a 1001bp snapshot on the two breakpoints of the inversion, and create a png file `19-16780041-16782041.19-17553189-17555189.inversion.tumor.png` in the OUTDIR.
4. The fourth region will take a 1001bp snapshot on the two breakpoints and a region inbetween, and create a png file `19-12874447-12876447.19-13500000-13501000.19-14461465-14463465.duplication.tumor.png` in the OUTDIR.
```
1:122535169-112537169 region_of_iterest
8:32534767-32536767 19:11137898-11139898 translocation
19:16780041-16782041 19:17553189-17555189 inversion
19:12874447-12876447 19:13500000-13501000 19:14461465-14463465 duplication
```

# Example results
You can see the IGV snapshots in `test/snapshots`.

1. [region_of_iterest](test/snapshots/1-122535169-112537169.region_of_interest.tumor.png) <br>
![](test/snapshots/1-122535169-112537169.region_of_interest.tumor.png)
2. [translocation](test/snapshots/8-32534767-32536767.19-11137898-11139898.translocation.tumor.png) <br>
![](test/snapshots/8-32534767-32536767.19-11137898-11139898.translocation.tumor.png)
3. [inversion](test/snapshots/19-16780041-16782041.19-17553189-17555189.inversion.tumor.png) <br>
![](test/snapshots/19-16780041-16782041.19-17553189-17555189.inversion.tumor.png)
4. [duplication](test/snapshots/19-12874447-12876447.19-13500000-13501000.19-14461465-14463465.duplication.tumor.png)<br>
![](test/snapshots/19-12874447-12876447.19-13500000-13501000.19-14461465-14463465.duplication.tumor.png)

