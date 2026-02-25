FROM us-docker.pkg.dev/sysdig-artifact-registry-dev/gar-docker/mirror/alpine:3.22

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
RUN /usr/bin/pip install --break-system-packages -e .
ENTRYPOINT [ "/builder/main-builder-entrypoint.sh" ]

