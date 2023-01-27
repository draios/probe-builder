import errno
import logging
import os
import subprocess
import time

import click

from probe_builder import docker
from probe_builder.builder import builder_image, choose_builder
from probe_builder.kernel_crawler import crawl_kernels
from probe_builder.kernel_crawler.download import download_batch
from probe_builder.py23 import make_bytes, make_string

logger = logging.getLogger(__name__)


def to_s(s):
    if s is None:
        return ''
    else:
        return str(s)


class DistroBuilder(object):
    class ProbeBuildResult(object):
        BUILD_BUILT=0
        BUILD_EXISTING=1
        BUILD_SKIPPED=2
        BUILD_FAILED=3
        def __init__(self, build_result, build_time=0, error_log=b''):
            self.build_time = build_time
            self.build_result = build_result
            self.error_log = error_log

        def build_result_string(self):
            mydict = {
                self.BUILD_BUILT: 'BUILT',
                self.BUILD_EXISTING: 'EXISTING',
                self.BUILD_SKIPPED: 'SKIPPED',
                self.BUILD_FAILED: 'FAILED',
            }
            return mydict[self.build_result]

        def failed(self):
            return self.build_result == self.BUILD_FAILED

    class KernelBuildResult(object):
        def __init__(self, kmod_result, ebpf_result):
            self.kmod_result = kmod_result
            self.ebpf_result = ebpf_result

        def failed(self):
            return self.kmod_result.failed() or self.ebpf_result.failed()

    @staticmethod
    def md5sum(path):
        from hashlib import md5
        digest = md5()
        with open(path) as fp:
            digest.update(fp.read().encode('utf-8'))
        return digest.hexdigest()

    def unpack_kernels(self, workspace, distro, kernels):
        raise NotImplementedError

    def hash_config(self, release, target):
        raise NotImplementedError

    def get_kernel_dir(self, workspace, release, target):
        raise NotImplementedError

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
        if builder_image.probe_built(probe, output_dir, release, config_hash, bpf):
            return cls.ProbeBuildResult(cls.ProbeBuildResult.BUILD_EXISTING, 0)

        if skip_reason:
            logger.info('Skipping build of {} probe {}-{}: {}'.format(label, release, config_hash, skip_reason))
            return cls.ProbeBuildResult(cls.ProbeBuildResult.BUILD_SKIPPED, 0)

        #docker.rm(container_name)
        try:
            ts0 = time.time()
            stdout = builder_image.run(workspace, probe, kernel_dir, release, config_hash, container_name, image_name, args)
        except subprocess.CalledProcessError as e:
            took = time.time() - ts0
            logger.error("Build failed for {} probe {}-{} (took {:.3f}s)".format(label, release, config_hash, took))
            return cls.ProbeBuildResult(cls.ProbeBuildResult.BUILD_FAILED, took, e.output)
        else:
            took = time.time() - ts0
            if builder_image.probe_built(probe, output_dir, release, config_hash, bpf):
                logger.info("Build for {} probe {}-{} successful (took {:.3f}s)".format(label, release, config_hash, took))
                return cls.ProbeBuildResult(cls.ProbeBuildResult.BUILD_BUILT, took)
            else:
                logger.warn("Build for {} probe {}-{} failed silently: no output file found".format(label, release, config_hash))
                for line in stdout.splitlines(False):
                    logger.warn(make_string(line))
                return cls.ProbeBuildResult(cls.ProbeBuildResult.BUILD_FAILED, took, stdout)

    def build_kernel(self, workspace, probe, builder_distro, release, target):
        config_hash = self.hash_config(release, target)
        output_dir = workspace.subdir('output')

        kmod_skip_reason = builder_image.skip_build(probe, output_dir, release, config_hash, False)
        ebpf_skip_reason = builder_image.skip_build(probe, output_dir, release, config_hash, True)
        try:
            os.makedirs(output_dir, 0o755)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise

        kernel_dir = self.get_kernel_dir(workspace, release, target)
        dockerfile, dockerfile_tag, support_bpf = choose_builder.choose_dockerfile(workspace.builder_source, builder_distro,
                                                                    kernel_dir)

        ts0 = time.time()
        # let build() figure out if it actually needs to build or pull anything
        builder_image.build(workspace, dockerfile, dockerfile_tag)
        took = time.time() - ts0

        logger.info("Docker building of {} took {:.2f}s".format(dockerfile, took))

        if not support_bpf:
            ebpf_skip_reason = "Builder {} does not support eBPF".format(dockerfile)

        image_name = '{}sysdig-probe-builder:{}'.format(workspace.image_prefix, dockerfile_tag)
        #container_name = 'sysdig-probe-builder-{}'.format(dockerfile_tag)
        container_name = ''

        return self.KernelBuildResult(
            self.build_kernel_impl(config_hash, container_name, image_name, kernel_dir, probe, release, workspace, False,
                                kmod_skip_reason),
            self.build_kernel_impl(config_hash, container_name, image_name, kernel_dir, probe, release, workspace, True,
                                ebpf_skip_reason),
        )

    def batch_packages(self, kernel_files):
        raise NotImplementedError

    def crawl(self, workspace, distro, crawler_distro, download_config=None, filter=''):
        kernels = crawl_kernels(crawler_distro, filter)
        try:
            os.makedirs(workspace.subdir(distro.distro))
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise
        # kernels is a dict {'release'=>['urls'...]}
        all_urls = []
        kernel_files = {}
        for release, urls in kernels.items():
            all_urls.extend(urls)
            kernel_files[release] = [workspace.subdir(distro.distro, os.path.basename(url)) for url in urls]

        with click.progressbar(all_urls, label='Downloading kernels', item_show_func=to_s) as all_urls:
            download_batch(all_urls, workspace.subdir(distro.distro), download_config)

        # kernel_files is a dict {'release'=>['/local/path/to/files'....]}
        return kernel_files
