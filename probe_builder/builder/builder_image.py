import logging
import os

from .. import docker
from ..version import Version
import threading

logger = logging.getLogger(__name__)

# TODO here perhaps we might want to make a class?
#class BuilderImage:

# cache the builders we have already built, so that we only
# do this once
builders = {}
builders_lock = threading.Lock()

def build(workspace, dockerfile, dockerfile_tag):
    with builders_lock:
        k = (dockerfile, dockerfile_tag)
        obj = builders.get(k)
        if obj is not None:
            return obj
        # for now we only cache the fact that the builder has been built...
        obj = True
        # ... but if we make this a factory @staticmethod of a proper class, we'll have to do this:
        #obj = cls()

        image_name = '{}sysdig-probe-builder:{}'.format(workspace.image_prefix, dockerfile_tag)
        if workspace.image_prefix:
            # image_prefix essentially means: we got this prebuilt (possibly from a docker repo)
            pass
        else:
            # otherwise, we'll have to built it ourselves
            docker.build(image_name, dockerfile, workspace.builder_source)

        # cache the object
        builders[k] = obj
        return obj

def run(workspace, probe, kernel_dir, kernel_release,
        config_hash, container_name, image_name, sign_file_hash_algo, args):
    volumes = [
        docker.DockerVolume(workspace.host_dir(probe.sysdig_dir), '/code/sysdig-ro', True),
        docker.DockerVolume(workspace.host_workspace(), '/build/probe', True),
        docker.DockerVolume(workspace.host_workspace() + "/output", '/output', False),
    ]
    env = [
        docker.EnvVar('OUTPUT', '/output'),
        docker.EnvVar('PROBE_NAME', probe.probe_name),
        docker.EnvVar('PROBE_VERSION', probe.probe_version),
        docker.EnvVar('PROBE_DEVICE_NAME', probe.probe_device_name),
        docker.EnvVar('KERNELDIR', kernel_dir.replace(workspace.workspace, '/build/probe/')),
        docker.EnvVar('KERNEL_RELEASE', kernel_release),
        docker.EnvVar('HASH', config_hash),
        docker.EnvVar('HASH_ORIG', config_hash),
        docker.EnvVar('SIGN_FILE_HASH_ALGO', sign_file_hash_algo),
    ]

    return docker.run(image_name, volumes, args, env, name=container_name)


def probe_output_file(probe, kernel_release, config_hash, bpf):
    arch = os.uname()[4]
    if bpf:
        return '{}-bpf-{}-{}-{}-{}.o'.format(
            probe.probe_name, probe.probe_version, arch, kernel_release, config_hash
        )
    else:
        return '{}-{}-{}-{}-{}.ko'.format(
            probe.probe_name, probe.probe_version, arch, kernel_release, config_hash
        )


SKIPPED_KERNELS = [
    ("4.15.0-29-generic", "ea0aa038a6b9bdc4bb42152682bba6ce"),
    ("4.9.0-4-grsec-amd64", "1ff376e85cab19e75e0ef64d837af78d"),
    ("5.8.0-1023-aws", "3f7746be1bef4c3f68f5465d8453fa4d"),
]


# These AmazonLinux2 kernels were built with gcc 10.
# Apparently, starting with 5.10.50, they started creating a
# wrapper /usr/src/kernels/*/Makefile containing the following:
#
# GCC_VER=gcc10-
# CROSS_COMPILE=$(GCC_VER)
# HOSTCC=$(GCC_VER)gcc
# HOSTCXX=$(GCC_VER)g++
# CC=$(GCC_VER)gcc
# LD=$(GCC_VER)ld.bfd
#
# which would then call the renamed Makefile->Makefile.kernel
# so these 4 guys are essentially broken so we just exclude them
#
SKIPPED_AL2_KMOD_KERNELS = [
    ("5.10.47-39.130.amzn2.x86_64", "c2f4afab82d814c0917176b3e8bbc5eb"),
    ("5.10.35-31.135.amzn2.x86_64", "72045c5b99c571a8dfffc5b537912864"),
    ("5.10.29-27.126.amzn2.x86_64", "587d839a59252859091e65c52f202a92"),
    ("5.10.29-27.128.amzn2.x86_64", "94f8e35b13a393ca58b765bd738e2562"),
]

def probe_built(probe, output_dir, kernel_release, config_hash, bpf):
    probe_file_name = probe_output_file(probe, kernel_release, config_hash, bpf)
    return os.path.exists(os.path.join(output_dir, probe_file_name))

def skip_build(probe, output_dir, kernel_release, config_hash, bpf):
    if probe_built(probe, output_dir, kernel_release, config_hash, bpf):
        return "Already built"

    if (kernel_release, config_hash) in SKIPPED_KERNELS:
        return "Unsupported kernel"
    if bpf:
        kernel_version = Version(kernel_release)
        if kernel_version < Version('4.14'):
            return 'Kernel {} too old to support eBPF (need at least 4.14)'.format(kernel_release)
    else:
        if (kernel_release, config_hash) in SKIPPED_AL2_KMOD_KERNELS:
            return "AmazonLinux2 kernel built with gcc-10 but without wrapper Makefile"
