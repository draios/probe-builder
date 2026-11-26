import logging
import os
import re

import click

from probe_builder.builder import toolkit
from .base_builder import DistroBuilder

logger = logging.getLogger(__name__)


class CentosBuilder(DistroBuilder):
    RPM_KERNEL_RELEASE_RE = re.compile(r'^kernel-(uek-)?(core-|devel-|modules-)?(?P<release>.*)\.rpm$')

    def unpack_kernels(self, workspace, distro, kernels):
        kernel_dirs = list()
        for (drel, krel), rpms in kernels.items():
            target = workspace.subdir('build', distro, krel)
            kernel_dirs.append(((drel,krel), target))

            for rpm in rpms:
                rpm_basename = os.path.basename(rpm)
                marker = os.path.join(target, '.' + rpm_basename)
                toolkit.unpack_rpm(workspace, rpm, target, marker)

        return kernel_dirs

    @staticmethod
    def config_paths(release, target):
        # Candidate locations of the kernel config, in order of preference.
        # The config ships in kernel-core.
        return [
            os.path.join(target, 'boot/config-{}'.format(release)),
            os.path.join(target, 'lib/modules/{}/config'.format(release)),
        ]

    def hash_config(self, release, target):
        paths = self.config_paths(release, target)
        # Fall back to the last candidate so a missing config raises the same error as before.
        return self.md5sum(next((p for p in paths if os.path.isfile(p)), paths[-1]))

    def incomplete_kernel_reason(self, release, target):
        # The config comes from kernel-core, the headers/sources from kernel-devel.
        # A custom kernel may only have one of the two, so report it instead of failing.
        config_paths = self.config_paths(release, target)
        if not any(os.path.isfile(p) for p in config_paths):
            return 'kernel-core missing: expected one of {}'.format(', '.join(config_paths))
        devel_path = os.path.join(target, 'usr/src/kernels', release)
        if not os.path.isdir(devel_path):
            return 'kernel-devel missing: expected directory {}'.format(devel_path)
        return None

    def get_kernel_dir(self, workspace, release, target):
        return workspace.subdir(target, 'usr/src/kernels', release)

    def batch_packages(self, kernel_files):
        kernels = dict()
        for rpm in kernel_files:
            rpm_filename = os.path.basename(rpm)
            m = self.RPM_KERNEL_RELEASE_RE.match(rpm_filename)
            if not m:
                click.echo("Filename {} doesn't look like a kernel package".format(rpm_filename), err=True)
                continue
            kernels.setdefault(m.group('release'), []).append(rpm)

        return kernels
