FROM alpine:3.16

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
	qemu-s390x \
    docker

RUN ln -s /usr/bin/python3 /usr/bin/python
RUN cp -f /usr/bin/qemu-s390x /usr/bin/qemu-s390x-static

ADD . /builder
WORKDIR /builder
RUN /usr/bin/pip install -e .
ENTRYPOINT [ "/builder/main-builder-entrypoint.sh" ]

