from probe_builder.builder import toolkit
from probe_builder.kernel_crawler.repo import EMPTY_FILTER
from .centos import CentosBuilder


class PhotonosBuilder(CentosBuilder):
    @staticmethod
    def strip_release(release):
        # remove trailing arch, if any
        if release.endswith(".x86_64"):
            return release[: -len(".x86_64")]
        return release

    def crawl(self, workspace, distro, crawler_distro, download_config=None, crawler_filter=EMPTY_FILTER):
        # call the parent's method
        orig = super().crawl(
            workspace=workspace,
            distro=distro,
            crawler_distro=crawler_distro,
            download_config=download_config,
            crawler_filter=crawler_filter,
        )
        # make up a new list with stripped release version
        renamed = {}
        for release, urls in orig.items():
            renamed[self.strip_release(release)] = urls
        return renamed

    def get_kernel_dir(self, workspace, release, target):
        # Photon OS is rpm based but the kernel dir structure is the debian one ¯\_(ツ)_/¯
        return workspace.subdir(target, "usr/src/linux-headers-{}".format(release))
