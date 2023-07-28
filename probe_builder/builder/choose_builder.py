import os
import logging
import re
import glob

from ..version import Version

logger = logging.getLogger(__name__)

AUTOCONF_RE = re.compile('^#define CONFIG_GCC_VERSION ([0-9][0-9]?)([0-9][0-9])([0-9][0-9])$')
LINUX_COMPILER_RE = re.compile('^#define LINUX_COMPILER "gcc version ([0-9.]+)')
FEDORA_KERNEL_RE = re.compile(r'.*\.(fc[0-9]+)\..*Kernel Configuration$')
AMAZONLINUX2_KERNEL_RE = re.compile(r'.*\.amzn2\..*Kernel Configuration$')


def get_kernel_distro_tag(kernel_dir):
    # Try to find a distro-specific builder based on the version
    # embedded in the header of autoconf.h
    # /*
    #  *
    #  * Automatically generated file; DO NOT EDIT.
    #  * Linux/x86_64 5.15.5-100.fc34.x86_64 Kernel Configuration
    #  *
    #  */
    try:
        logger.debug('checking {} for distro tag'.format(os.path.join(kernel_dir, "include/generated/autoconf.h")))
        with open(os.path.join(kernel_dir, "include/generated/autoconf.h")) as fp:
            for line in fp:
                m = FEDORA_KERNEL_RE.match(line)
                if m:
                    distro_tag = m.group(1)
                    return distro_tag
                m = AMAZONLINUX2_KERNEL_RE.match(line)
                if m:
                    return 'amzn2'
    except IOError:
        pass


def choose_distro_dockerfile(builder_source, _builder_distro, kernel_dir):
    # Look for a distro-specific tag within the source header files
    distro_tag = get_kernel_distro_tag(kernel_dir)
    if distro_tag is None:
        return

    # if we have a distro tag (e.g. fc34), look for that exact Dockerfile.fc34* (modulo the -bpf suffix)
    dockerfile = os.path.join(builder_source, 'Dockerfile.{}'.format(distro_tag))
    m = glob.glob(dockerfile+'*')
    if m:
        fn = m[0]
        return fn, distro_tag, fn.endswith("-bpf")

def all_dockerfiles(builder_source):
    prefix = "Dockerfile."
    return [
        (f, f.replace(prefix,'')) for f in os.listdir(builder_source) if f.startswith(prefix)
    ]

def get_kernel_gcc_version(kernel_dir):
    # Try to find the gcc version used to build this particular kernel
    # Check CONFIG_GCC_VERSION=90201 in the kernel config first
    # as 5.8.0 seems to have a different format for the LINUX_COMPILER string
    try:
        logger.debug('checking {} for gcc version'.format(os.path.join(kernel_dir, "include/generated/autoconf.h")))
        with open(os.path.join(kernel_dir, "include/generated/autoconf.h")) as fp:
            for line in fp:
                m = AUTOCONF_RE.match(line)
                if m:
                    version = [int(m.group(1)), int(m.group(2)), int(m.group(3))]
                    return '.'.join(str(s) for s in version)
    except IOError:
        pass

    # then, try the LINUX_COMPILER macro, in two separate files
    try:
        logger.debug('checking {} for gcc version'.format(os.path.join(kernel_dir, "include/generated/compile.h")))
        with open(os.path.join(kernel_dir, "include/generated/compile.h")) as fp:
            for line in fp:
                m = LINUX_COMPILER_RE.match(line)
                if m:
                    return m.group(1)
    except IOError:
        pass

    # RHEL 6
    try:
        logger.debug('checking {} for gcc version'.format(os.path.join(kernel_dir, "include/compile.h")))
        with open(os.path.join(kernel_dir, "include/compile.h")) as fp:
            for line in fp:
                m = LINUX_COMPILER_RE.match(line)
                if m:
                    return m.group(1)
    except IOError:
        pass

    # ancient Ubuntu gets an ancient compiler
    return '4.8.0'


def choose_gcc_dockerfile(builder_source, builder_distro, kernel_dir):
    kernel_gcc = get_kernel_gcc_version(kernel_dir)
    logger.debug('kernel gcc version: {}'.format(kernel_gcc))

    # We don't really care about the compiler patch levels, only the major/minor version
    kernel_gcc = Version(kernel_gcc)
    logger.debug('found kernel gcc version {}'.format(kernel_gcc))

    # Choose the right gcc version from the ones we have available (as Docker images)
    # - if we have the exact minor version, use it
    # - if not, and there's a newer compiler version, use that
    #   (as close to the requested version as possible)
    # - if there are no newer compilers, use the newest one we have
    #   it will be older than the requested one but hopefully
    #   not by much
    #
    # This means we don't have to exactly follow all distro gcc versions
    # (indeed, we don't e.g. for AmazonLinux) but only need to add a new
    # Dockerfile when the latest kernel fails to build with our newest
    # gcc for that distro

    # The dockerfiles in question all look like .../Dockerfile.centos-gcc4.4
    # or similar. We want to pick the one that's closest to `kernel_gcc`
    # (exact match, slightly newer, slightly older, in that order of preference).
    # To do that, we iterate over the list of all available dockerfiles (i.e. gcc
    # versions) for a particular distribution in ascending version order (oldest->newest).
    # To get actual sorting by version numbers, we strip the common prefix first
    # and add it back after finding the best available version. What we're sorting is:
    #   4.4
    #   9.2
    #   10.0
    # and now we properly realize that gcc 10 is newer than 9.2, not older than 4.4

    # we're looking for something like Dockerfile.<builder_distro>-gcc<gcc_version>[-bpf]
    #                                  ^------prefix-----------------^
    prefix = 'Dockerfile.{}-gcc'.format(builder_distro)
    # build a regex from which we can extract all available gcc versions
    # NOTE: for now we're having the consumer figure the logic by itself
    regex = re.compile('^' + re.escape(prefix) + '(?P<gccver>[0-9]+\.[0-9]+)(?P<bpf>(\-bpf)?)$')

    # build a list of (filename, [GCC-]Version, support_bpf) tuples
    dockerfile_versions = [
        (f, Version(regex.match(f).group('gccver')), regex.match(f).group('bpf') != "")
        for f in os.listdir(builder_source)
        if regex.match(f)
    ]
    # sort by Version (using semantic versioning)
    dockerfile_versions.sort(key=lambda t: t[1])
    logger.debug('available (dockerfile, gcc-version, support-bpf) combinations: {!r}'.format(dockerfile_versions))

    # mind: exact match, slightly newer, slightly older, in that order of preference
    dockerfile_version = (None, None, False)
    for _ in dockerfile_versions:
        dockerfile_version = _
        if dockerfile_version[1] >= kernel_gcc:
            break

    # only get the dockerfile and whether it supports bpf from the tuple
    dockerfile, _, support_bpf = dockerfile_version
    # get a tag we'll use for builders
    tag = dockerfile.replace('Dockerfile.', '')
    logger.debug('chosen dockerfile for the builder: {}'.format(dockerfile))
    # return the tuple ("/path/to/Dockerfile.centos-gcc11.0-bpf", "gcc11.0-bpf", True)
    return os.path.join(builder_source, dockerfile), tag, support_bpf


# return the tuple ("/path/to/Dockerfile.centos-gcc11.0-bpf", "gcc11.0-bpf", True)
def choose_dockerfile(builder_source, builder_distro, kernel_dir):
    # First, let'see if we can find a dockerfile for the exact same kernel distro
    dockerfile_with_tag = choose_distro_dockerfile(builder_source, builder_distro, kernel_dir)
    if dockerfile_with_tag is not None:
        return dockerfile_with_tag

    # If not, let's find one with the same builder distro and gcc version
    return choose_gcc_dockerfile(builder_source, builder_distro, kernel_dir)
