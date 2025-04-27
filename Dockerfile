FROM nvidia/cuda:12.8.0-base-ubuntu24.04 as builder

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Moscow
ARG FFMPEG_VERSION=7.1.1

# Install dependencies
RUN apt-get update -yqq \
    && apt-get install -yqq --no-install-recommends \
    apt-utils \
    apt-transport-https \
    ca-certificates \
    gnupg \
    software-properties-common \
    lsb-release \
    wget \
    && add-apt-repository ppa:apt-fast/stable \
    && apt-get -yqq install apt-fast


RUN echo 'debconf apt-fast/maxdownloads string 16' | debconf-set-selections
RUN echo 'debconf apt-fast/dlflag boolean true' | debconf-set-selections
RUN echo 'debconf apt-fast/aptmanager string apt-get' | debconf-set-selections

# Install dependencies
RUN apt-get update && apt-get -yqq install  \
    doxygen \
    debhelper \
    flite1-dev \
    frei0r-plugins-dev \
    ladspa-sdk \
    build-essential \
    libaom-dev \
    libaribb24-dev \
    libass-dev \
    libbluray-dev \
    libbs2b-dev \
    libglx-dev \
    libglx-mesa0 \
    libbz2-dev \
    libcaca-dev \
    libcdio-paranoia-dev \
    libchromaprint-dev \
    libcodec2-dev \
    libdrm-dev \
    libfdk-aac-dev \
    libfontconfig1-dev \
    libfreetype6-dev \
    libfribidi-dev \
    libgl1-mesa-dev \
    libgme-dev \
    libgnutls28-dev \
    libgsm1-dev \
    libiec61883-dev \
    libavc1394-dev \
    libjack-jackd2-dev \
    liblensfun-dev \
    liblilv-dev \
    liblzma-dev \
    libmp3lame-dev \
    libmysofa-dev \
    libnvidia-compute-470-server \
    libnvidia-decode-470-server \
    libnvidia-encode-470-server \
    libopenal-dev \
    libomxil-bellagio-dev \
    libopencore-amrnb-dev \
    libopencore-amrwb-dev \
    libopenjp2-7-dev \
    libopenmpt-dev \
    libopus-dev \
    libpulse-dev \
    librubberband-dev \
    librsvg2-dev \
    libsctp-dev \
    libsdl2-dev \
    libshine-dev \
    libsnappy-dev \
    libsoxr-dev \
    libspeex-dev \
    libssh-gcrypt-dev \
    libtesseract-dev \
    libtheora-dev \
    libtwolame-dev \
    libva-dev \
    libvdpau-dev \
    libvidstab-dev \
    libvo-amrwbenc-dev \
    libvorbis-dev \
    libvpx-dev \
    libwavpack-dev \
    libwebp-dev \
    libx264-dev \
    libx265-dev \
    libxcb-shape0-dev \
    libxcb-shm0-dev \
    libxcb-xfixes0-dev \
    libxml2-dev \
    libxv-dev \
    libxvidcore-dev \
    libxvmc-dev \
    libzmq3-dev \
    libzvbi-dev \
    nasm \
    node-less \
    ocl-icd-opencl-dev \
    pkg-config \
    wget \
    zlib1g-dev


RUN apt-get update && apt-get install -y \
    libffmpeg-nvenc-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Build ffmpeg
RUN wget -O /ffmpeg-${FFMPEG_VERSION}.tar.gz https://ffmpeg.org/releases/ffmpeg-${FFMPEG_VERSION}.tar.gz \
    && tar -xf /ffmpeg-${FFMPEG_VERSION}.tar.gz \
    && rm /ffmpeg-${FFMPEG_VERSION}.tar.gz \
    && cd /ffmpeg-${FFMPEG_VERSION} \
    && ./configure --prefix=/usr/local/ffmpeg-nvidia \
        --extra-cflags=-I/usr/local/cuda/include \
        --extra-ldflags=-L/usr/local/cuda/lib64 \
        --toolchain=hardened \
        --enable-gpl \
        --disable-stripping \
        --disable-filter=resample \
        --enable-cuvid \
        --enable-gnutls \
        --enable-ladspa \
        --enable-libaom \
        --enable-libass \
        --enable-libbluray \
        --enable-libbs2b \
        --enable-libcaca \
        --enable-libcdio \
        --enable-libcodec2 \
        --enable-libfdk-aac \
        --enable-libflite \
        --enable-libfontconfig \
        --enable-libfreetype \
        --enable-libfribidi \
        --enable-libgme \
        --enable-libgsm \
        --enable-libjack \
        --enable-libmp3lame \
        --enable-libmysofa \
        --enable-libopenjpeg \
        --enable-libopenmpt \
        --enable-libopus \
        --enable-libpulse \
        --enable-librsvg \
        --enable-librubberband \
        --enable-libshine \
        --enable-libsnappy \
        --enable-libsoxr \
        --enable-libspeex \
        --enable-libssh \
        --enable-libtheora \
        --enable-libtwolame \
        --enable-libvorbis \
        --enable-libvidstab \
        --enable-libvpx \
        --enable-libwebp \
        --enable-libx265 \
        --enable-libxml2 \
        --enable-libxvid \
        --enable-libzmq \
        --enable-libzvbi \
        --enable-lv2 \
        --enable-nvenc \
        --enable-nonfree \
        --enable-omx \
        --enable-openal \
        --enable-opencl \
        --enable-opengl \
        --enable-sdl2 \
    && make -j $(nproc) \
    && make install \
    && ls /usr/local/ffmpeg-nvidia 

RUN ls /usr/local/ffmpeg-nvidia 




FROM nvidia/cuda:12.8.0-base-ubuntu24.04

# Install dependencies
RUN apt-get update -yqq \
    && apt-get install -yqq --no-install-recommends \
    apt-utils \
    apt-transport-https \
    ca-certificates \
    gnupg \
    software-properties-common \
    lsb-release \
    wget \
    && add-apt-repository ppa:apt-fast/stable \
    && apt-get -yqq install apt-fast

RUN apt-get update && apt-get install -yqq \
    python3 \
    python3-pip \
    libglx-mesa0 \
    ffmpeg \
    libaom-dev \
    libaribb24-dev \
    libass-dev \
    libbluray-dev \
    libbs2b-dev \
    libglx-dev \
    libglx-mesa0 \
    libbz2-dev \
    libcaca-dev \
    libcdio-paranoia-dev \
    libchromaprint-dev \
    libcodec2-dev \
    libdrm-dev \
    libfdk-aac-dev \
    libfontconfig1-dev \
    libfreetype6-dev \
    libfribidi-dev \
    libgl1-mesa-dev \
    libgme-dev \
    libgnutls28-dev \
    libgsm1-dev \
    libiec61883-dev \
    libavc1394-dev \
    libjack-jackd2-dev \
    liblensfun-dev \
    liblilv-dev \
    liblzma-dev \
    libmp3lame-dev \
    libmysofa-dev \
    libnvidia-compute-470-server \
    libnvidia-decode-470-server \
    libnvidia-encode-470-server \
    libopenal-dev \
    libomxil-bellagio-dev \
    libopencore-amrnb-dev \
    libopencore-amrwb-dev \
    libopenjp2-7-dev \
    libopenmpt-dev \
    libopus-dev \
    libpulse-dev \
    librubberband-dev \
    librsvg2-dev \
    libsctp-dev \
    libsdl2-dev \
    libshine-dev \
    libsnappy-dev \
    libsoxr-dev \
    libspeex-dev \
    libssh-gcrypt-dev \
    libtesseract-dev \
    libtheora-dev \
    libtwolame-dev \
    libva-dev \
    libvdpau-dev \
    libvidstab-dev \
    libvo-amrwbenc-dev \
    libvorbis-dev \
    libvpx-dev \
    libwavpack-dev \
    libwebp-dev \
    libx264-dev \
    libx265-dev \
    libxcb-shape0-dev \
    libxcb-shm0-dev \
    libxcb-xfixes0-dev \
    libxml2-dev \
    libxv-dev \
    libxvidcore-dev \
    libxvmc-dev \
    libzmq3-dev \
    libzvbi-dev \
    nasm \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*


COPY --from=builder /usr/local/ffmpeg-nvidia /usr/local/ffmpeg-nvidia

