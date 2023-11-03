import errno
import glob
import logging
import os
import subprocess
import time

import click

from .base_builder import DistroBuilder, to_s
from .. import toolkit, builder_image
from ... import crawl_kernels, docker
from ...kernel_crawler.download import download_file
from ...kernel_crawler.repo import EMPTY_FILTER
from probe_builder.py23 import make_bytes, make_string

logger = logging.getLogger(__name__)


class FlatcarBuilder(DistroBuilder):
    def unpack_kernels(self, workspace, distro, kernels):
        kernel_dirs = list()

        logger.info("Kernels: {}".format(kernels))

        for (drel, krel), dev_containers in kernels.items():
            target = workspace.subdir('build', distro, krel)
            kernel_dirs.append(((drel, krel), target))

            for dev_container in dev_containers:
                dev_container_basename = os.path.basename(dev_container)
                marker = os.path.join(target, '.' + dev_container_basename)
                toolkit.unpack_coreos(workspace, dev_container, target, marker)

        return kernel_dirs

    def hash_config(self, release, target):
        return self.md5sum(os.path.join(target, 'config'.format(release)))

    def get_kernel_dir(self, workspace, release, target):
        versions = glob.glob(os.path.join(target, 'modules/*/build'))
        if len(versions) != 1:
            raise RuntimeError('Expected one kernel version in {}, got: {!r}'.format(target, versions))
        return versions[0]

    def batch_packages(self, kernel_files):
        releases = {}
        for path in kernel_files:
            release, orig_filename = os.path.basename(path).split('-', 1)
            releases.setdefault(release, []).append(path)
        return releases

    @classmethod
    def build_kernel_impl(cls, config_hash, container_name, image_name, kernel_dir, probe, release, workspace, bpf,
                          skip_reason):
        if bpf:
            label = 'eBPF'
            args = ['bpf']
        else:
            label = 'kmod'
            args = []

        output_dir = workspace.subdir('output')
        coreos_kernel_release = os.path.basename(os.path.dirname(kernel_dir))

        if builder_image.probe_built(workspace.machine, probe, output_dir, coreos_kernel_release, config_hash, bpf):
            return cls.ProbeBuildResult(cls.ProbeBuildResult.BUILD_EXISTING, 0)

        if skip_reason:
            logger.info('Skipping build of {} probe {}-{} ({}): {}'.format(label, coreos_kernel_release, config_hash,
                                                                           release, skip_reason))
            return cls.ProbeBuildResult(cls.ProbeBuildResult.BUILD_SKIPPED, 0)

        #docker.rm(container_name)
        try:
            ts0 = time.time()
            stdout = builder_image.run(workspace, probe, kernel_dir, coreos_kernel_release, config_hash, container_name, image_name, args)
        except subprocess.CalledProcessError as e:
            took = time.time() - ts0
            logger.error("Build failed for {} probe {}-{} ({})".format(label, coreos_kernel_release, config_hash, release))
        else:
            took = time.time() - ts0
            if builder_image.probe_built(workspace.machine, probe, output_dir, coreos_kernel_release, config_hash, bpf):
                logger.info("Build for {} probe {}-{} ({}) successful".format(label, coreos_kernel_release, config_hash, release))
                return cls.ProbeBuildResult(cls.ProbeBuildResult.BUILD_BUILT, took)
            else:
                logger.warn("Build for {} probe {}-{} failed silently: no output file found".format(label, coreos_kernel_release, config_hash))
                for line in stdout.splitlines(False):
                    logger.warn(make_string(line))
                return cls.ProbeBuildResult(cls.ProbeBuildResult.BUILD_FAILED, took, stdout)


    def crawl(self, workspace, distro, crawler_distro, download_config=None, crawler_filter=EMPTY_FILTER):
        kernels = crawl_kernels(crawler_distro, crawler_filter=crawler_filter)
        try:
            os.makedirs(workspace.subdir(distro.distro))
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise

        all_urls = []
        kernel_files = {}
        for release, urls in kernels.items():
            _drel, krel = release
            all_urls.extend(urls)
            kernel_files[release] = [
                workspace.subdir(distro.distro, '{}-{}'.format(krel, os.path.basename(url))) for url in urls]

        with click.progressbar(all_urls, label='Downloading development containers', item_show_func=to_s) as all_urls:
            for url in all_urls:
                _, release, filename = url.rsplit('/', 2)
                output_file = workspace.subdir(distro.distro, '{}-{}'.format(release, filename))
                download_file(url, output_file, download_config)

        return kernel_files
