# docker build -f docker/Dockerfile --build-arg GIT_SHA=$(git rev-parse HEAD) -t sahuno/igver:latest .   (from the repo root)
# docker push sahuno/igver:latest

# setup: using archlinux because it was the only distro where I could find --auto-display
FROM archlinux:latest

RUN pacman -Syu --noconfirm  xorg-server-xvfb python wget pacman jdk-openjdk unzip git libxtst

# get IGV 2.19.8
RUN wget https://data.broadinstitute.org/igv/projects/downloads/2.19/IGV_2.19.8.zip && \
    unzip IGV_2.19.8.zip -d /opt && \
	rm IGV_2.19.8.zip
RUN mkdir -p /opt/IGV_2.19.8/genomes
# igver <= 1.2.0 defaults --igv-dir to /opt/IGV_2.19.5; keep it resolving against this image
RUN ln -s /opt/IGV_2.19.8 /opt/IGV_2.19.5

WORKDIR /opt/IGV_2.19.8

# font config
RUN pacman -Syu --noconfirm  gnu-free-fonts opendesktop-fonts ttf-dejavu fontconfig
RUN fc-cache -f -v

# install python packages
RUN pacman -Syu --noconfirm python-pip python-yaml python-matplotlib python-pillow python-cairosvg

# Install igver from the checkout being built (build context = repo root, see .dockerignore),
# not from a fresh clone of main: a later rebuild of a tag must contain that tag's code.
ARG GIT_SHA=unknown
LABEL org.opencontainers.image.revision=$GIT_SHA
COPY setup.py README.md requirements.txt MANIFEST.in LICENSE /opt/igver/
COPY igver /opt/igver/igver

# Editable install, so `--bind <checkout>:/opt/igver` tests a working tree against this image
# (using --break-system-packages for Arch Linux)
RUN cd /opt/igver && pip install --break-system-packages -e . && \
    echo "$GIT_SHA" > /opt/igver/BUILD_SHA

# create wrapper script for backward compatibility
RUN echo '#!/usr/bin/env python' > /opt/igver/igver.py && \
    echo 'from igver.cli import main' >> /opt/igver/igver.py && \
    echo 'if __name__ == "__main__":' >> /opt/igver/igver.py && \
    echo '    main()' >> /opt/igver/igver.py && \
    chmod +x /opt/igver/igver.py

ENV PATH="$PATH:/opt/igver:/opt/IGV_2.19.8"

# Set environment to indicate we're in a container
ENV IGVER_IN_CONTAINER=1

# add genomes (from https://github.com/igvteam/igv/wiki/Downloading-Hosted-Genomes-for-Offline-Use/26e9731ef36889a974b0b6fa94fce7b36d67543e#hosted-genome-list)
ADD docker/json/ASM294v2.json /opt/IGV_2.19.8/genomes/ASM294v2.json
ADD docker/json/ASM985889v3.json /opt/IGV_2.19.8/genomes/ASM985889v3.json
ADD docker/json/bosTau8.json /opt/IGV_2.19.8/genomes/bosTau8.json
ADD docker/json/bosTau9.json /opt/IGV_2.19.8/genomes/bosTau9.json
ADD docker/json/canFam3.json /opt/IGV_2.19.8/genomes/canFam3.json
ADD docker/json/canFam5.json /opt/IGV_2.19.8/genomes/canFam5.json
ADD docker/json/ce11.json /opt/IGV_2.19.8/genomes/ce11.json
ADD docker/json/danRer10.json /opt/IGV_2.19.8/genomes/danRer10.json
ADD docker/json/danRer11.json /opt/IGV_2.19.8/genomes/danRer11.json
ADD docker/json/dm3.json /opt/IGV_2.19.8/genomes/dm3.json
ADD docker/json/dm6.json /opt/IGV_2.19.8/genomes/dm6.json
ADD docker/json/dmel_r5.9.json /opt/IGV_2.19.8/genomes/dmel_r5.9.json
ADD docker/json/galGal6.json /opt/IGV_2.19.8/genomes/galGal6.json
ADD docker/json/gorGor4.json /opt/IGV_2.19.8/genomes/gorGor4.json
ADD docker/json/gorGor6.json /opt/IGV_2.19.8/genomes/gorGor6.json
ADD docker/json/hg18.json /opt/IGV_2.19.8/genomes/hg18.json
ADD docker/json/hg19.json /opt/IGV_2.19.8/genomes/hg19.json
ADD docker/json/hg38.json /opt/IGV_2.19.8/genomes/hg38.json
ADD docker/json/hg38_1kg.json /opt/IGV_2.19.8/genomes/hg38_1kg.json
ADD docker/json/macFas5.json /opt/IGV_2.19.8/genomes/macFas5.json
ADD docker/json/mm10.json /opt/IGV_2.19.8/genomes/mm10.json
ADD docker/json/mm9.json /opt/IGV_2.19.8/genomes/mm9.json
ADD docker/json/panPan2.json /opt/IGV_2.19.8/genomes/panPan2.json
ADD docker/json/panTro4.json /opt/IGV_2.19.8/genomes/panTro4.json
ADD docker/json/rn6.json /opt/IGV_2.19.8/genomes/rn6.json
ADD docker/json/sacCer3.json /opt/IGV_2.19.8/genomes/sacCer3.json
ADD docker/json/tair10.json /opt/IGV_2.19.8/genomes/tair10.json

# custom genome (hs1 from https://s3.amazonaws.com/igv.org.genomes/genomes.json)
ADD docker/json/hs1.json /opt/IGV_2.19.8/genomes/hs1.json

# New genomes for mm39
ADD docker/json/mm39.json /opt/IGV_2.19.8/genomes/mm39.json

RUN chmod -R 777 /opt