FROM alpine:3.22

ARG TARGETARCH

RUN apk add \
    bash \
    gawk \
    grep \
	curl \
    dpkg \
	rpm2cpio \
	git \
	jq \
	multipath-tools \
	python3 \
	py3-pip \
	py3-lxml \
	sed \
	sfdisk \
	wget \
	docker-cli-buildx \
    docker

ADD . /builder
WORKDIR /builder
# pip's certifi bundle lacks the emSign root used by some mirrors (e.g. fedora.osuosl.org)
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
RUN /usr/bin/pip install --break-system-packages -e .
ENTRYPOINT [ "/builder/main-builder-entrypoint.sh" ]

