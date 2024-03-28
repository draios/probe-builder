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

	# Make sure we've been passed a full checkout of libs,
	# (on which we're forced to be running cmake to configure)
	# as opposed to an already-configured source package
	if [[ ! -e ${SRC_DIR}/CMakeLists.txt ]]; then
		return 1
	fi

	PROBE_NAME_PARAM=PROBE_NAME
	PROBE_VERSION_PARAM=PROBE_VERSION
	PROBE_DEVICE_NAME_PARAM=PROBE_DEVICE_NAME
	if [[ -f ${SRC_DIR}/driver/API_VERSION ]]; then
		# New param naming
		PROBE_NAME_PARAM=DRIVER_NAME
		PROBE_VERSION_PARAM=DRIVER_VERSION
		PROBE_DEVICE_NAME_PARAM=DRIVER_DEVICE_NAME
	fi
	cmake -DBUILD_BPF=On -DCMAKE_BUILD_TYPE=Release -D${PROBE_NAME_PARAM}=$PROBE_NAME -D${PROBE_VERSION_PARAM}=$PROBE_VERSION -D${PROBE_DEVICE_NAME_PARAM}=$PROBE_DEVICE_NAME -DCREATE_TEST_TARGETS=OFF ${SRC_DIR}
}

build_kmod() {
	if [[ -f "${KERNELDIR}/scripts/gcc-plugins/stackleak_plugin.so" ]]; then
		echo "Rebuilding gcc plugins for ${KERNELDIR}"
		(cd "${KERNELDIR}" && make gcc-plugins)
	fi

	echo Building $PROBE_NAME-$PROBE_VERSION-$ARCH-$KERNEL_RELEASE-$HASH.ko

	mkdir -p /build/sysdig
	cd /build/sysdig

	# Glue code for backwards compatibility with a plain libs/ checkout
	if call_cmake /code/sysdig-rw; then
		# cmake was successful, we'll run 'make' from within the
		# /build/sysdig directory where cmake copied all files for us
		make -C /build/sysdig driver
		BUILD_DIR=/build/sysdig/driver
	else
		# cmake failed, so we're probably dealing with an agent-kmodule.tgz
		# package file and we can therefore run make from the source tree
		# (without the driver/ prefix)
		BUILD_DIR=/code/sysdig-rw
		make -C $BUILD_DIR all
	fi
	strip -g $BUILD_DIR/$PROBE_NAME.ko

	KO_VERSION=$(/sbin/modinfo $BUILD_DIR/$PROBE_NAME.ko | grep vermagic | tr -s " " | cut -d " " -f 2)
	if [ "$KO_VERSION" != "$KERNEL_RELEASE" ]; then
		echo "Corrupted probe, KO_VERSION " $KO_VERSION ", KERNEL_RELEASE " $KERNEL_RELEASE
		exit 1
	fi

	cp $BUILD_DIR/$PROBE_NAME.ko $OUTPUT/$PROBE_NAME-$PROBE_VERSION-$ARCH-$KERNEL_RELEASE-$HASH.ko
	cp $BUILD_DIR/$PROBE_NAME.ko $OUTPUT/$PROBE_NAME-$PROBE_VERSION-$ARCH-$KERNEL_RELEASE-$HASH_ORIG.ko
}


build_bpf() {
	if ! type -p $CLANG > /dev/null
	then
		echo "$CLANG not available, not building eBPF probe $PROBE_NAME-bpf-$PROBE_VERSION-$ARCH-$KERNEL_RELEASE-$HASH.o"
	else
		echo "Building eBPF probe $PROBE_NAME-bpf-$PROBE_VERSION-$ARCH-$KERNEL_RELEASE-$HASH.o"
		mkdir -p /build/sysdig
		cd /build/sysdig

		# Glue code for backwards compatibility with a plain libs/ checkout
		if call_cmake /code/sysdig-rw; then
			# for the eBPF probe, cmake will only render driver_config.h
			# in the source directory so we'll end up running
			# make from the source tree anyway (as opposed to the build directory)
			# After the kmod/bpf package split we need to use a different approach
			# so to copy the header files and trigger the configure system
			# Ref: https://github.com/falcosecurity/driverkit/commit/dd7a2f19c7775bc66e8308cae607c0a9513457d1
			make -C /build/sysdig bpf
			BUILD_DIR=/build/sysdig/driver
		else
			# cmake failed, so we're probably dealing with an agent-kmodule.tgz
			# package file and we can therefore run make from the source tree
			# (without the driver/ prefix)
			BUILD_DIR=/code/sysdig-rw
			make -C $BUILD_DIR/bpf clean all
		fi
		cp $BUILD_DIR/bpf/probe.o $OUTPUT/$PROBE_NAME-bpf-$PROBE_VERSION-$ARCH-$KERNEL_RELEASE-$HASH.o
	fi
}

# make a local copy of the source code so we can
# run cmake on it without altering the code on the host
rm -rf /code/sysdig-rw
cp -rf /code/sysdig-ro /code/sysdig-rw

case "${1:-}" in
	bpf) build_bpf;;
	"") build_kmod;;
	*) exit 1;;
esac
