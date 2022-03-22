#!/bin/bash

# required env vars:
# HASH
# HASH_ORIG
# KERNELDIR
# KERNEL_RELEASE
# OUTPUT
# PROBE_DEVICE_NAME
# PROBE_NAME
# PROBE_VERSION

# optional env vars
# CLANG
# LLC

export CLANG=${CLANG:-clang}
export LLC=${LLC:-llc}

set -euo pipefail

ARCH=$(uname -m)

call_cmake() {
	SRC_DIR=$1
	PROBE_NAME_PARAM=PROBE_NAME
	PROBE_VERSION_PARAM=PROBE_VERSION
	PROBE_DEVICE_NAME_PARAM=PROBE_DEVICE_NAME
	if [[ -f ${SRC_DIR}/driver/API_VERSION ]]; then
		# New param naming
		PROBE_NAME_PARAM=DRIVER_NAME
		PROBE_VERSION_PARAM=DRIVER_VERSION
		PROBE_DEVICE_NAME_PARAM=DRIVER_DEVICE_NAME
	fi
	cmake -DCMAKE_BUILD_TYPE=Release -D${PROBE_NAME_PARAM}=$PROBE_NAME -D${PROBE_VERSION_PARAM}=$PROBE_VERSION -D${PROBE_DEVICE_NAME_PARAM}=$PROBE_DEVICE_NAME -DCREATE_TEST_TARGETS=OFF ${SRC_DIR}
}

build_kmod() {
	if [[ -f "${KERNELDIR}/scripts/gcc-plugins/stackleak_plugin.so" ]]; then
		echo "Rebuilding gcc plugins for ${KERNELDIR}"
		(cd "${KERNELDIR}" && make gcc-plugins)
	fi

	echo Building $PROBE_NAME-$PROBE_VERSION-$ARCH-$KERNEL_RELEASE-$HASH.ko

	mkdir -p /build/sysdig
	cd /build/sysdig

	call_cmake /code/sysdig-rw
	make driver
	strip -g driver/$PROBE_NAME.ko

	KO_VERSION=$(/sbin/modinfo driver/$PROBE_NAME.ko | grep vermagic | tr -s " " | cut -d " " -f 2)
	if [ "$KO_VERSION" != "$KERNEL_RELEASE" ]; then
		echo "Corrupted probe, KO_VERSION " $KO_VERSION ", KERNEL_RELEASE " $KERNEL_RELEASE
		exit 1
	fi

	cp driver/$PROBE_NAME.ko $OUTPUT/$PROBE_NAME-$PROBE_VERSION-$ARCH-$KERNEL_RELEASE-$HASH.ko
	cp driver/$PROBE_NAME.ko $OUTPUT/$PROBE_NAME-$PROBE_VERSION-$ARCH-$KERNEL_RELEASE-$HASH_ORIG.ko
}


build_bpf() {
	if ! type -p $CLANG > /dev/null
	then
		echo "$CLANG not available, not building eBPF probe $PROBE_NAME-bpf-$PROBE_VERSION-$ARCH-$KERNEL_RELEASE-$HASH.o"
	else
		echo "Building eBPF probe $PROBE_NAME-bpf-$PROBE_VERSION-$ARCH-$KERNEL_RELEASE-$HASH.o"
		mkdir -p /build/sysdig
		cd /build/sysdig
		call_cmake /code/sysdig-rw
		make -C /code/sysdig-rw/driver/bpf clean all
		cp /code/sysdig-rw/driver/bpf/probe.o $OUTPUT/$PROBE_NAME-bpf-$PROBE_VERSION-$ARCH-$KERNEL_RELEASE-$HASH.o
	fi
}

rm -rf /code/sysdig-rw
cp -rf /code/sysdig-ro /code/sysdig-rw

case "${1:-}" in
	bpf) build_bpf;;
	"") build_kmod;;
	*) exit 1;;
esac
