import logging
import os

import requests
from lxml import html

from . import repo
logger = logging.getLogger(__name__)


class FlatcarRepository(repo.Repository):
    def __init__(self, base_url):
        self.base_url = base_url

    def get_package_tree(self, crawler_filter):
        release = os.path.basename(self.base_url.rstrip('/'))
        if crawler_filter.kernel_filter not in release:
            return {}
        dev_container = os.path.join(self.base_url, 'flatcar_developer_container.bin.bz2')
        return {release: [dev_container]}

    def __str__(self):
        return self.base_url


class FlatcarDistro(repo.Distro):
    CHANNELS = ['stable', 'beta', 'alpha']

    def get_mirrors(self, crawler_filter):
        mirrors = [FlatcarMirror('https://{}.release.flatcar-linux.net/{}-usr/'.format(channel, crawler_filter.arch)) for channel in self.CHANNELS]
        return mirrors

class FlatcarMirror(repo.Mirror):
    def __init__(self, base_url):
        self.base_url = base_url

#    def scan_repo(self, base_url):
    def list_drel_repos(self, crawler_filter):
        base_url = self.base_url
        dists = requests.get(base_url)
        dists.raise_for_status()
        dists = dists.content
        doc = html.fromstring(dists, base_url)
        dists = doc.xpath('/html/body//a[not(@href="../")]/@href')

        fdists = [dist.lstrip('./') for dist in dists
                if dist.endswith('/')
                and dist.startswith('./' + crawler_filter.distro_filter)
                and 'current' not in dist
                and '-' not in dist]

        logger.info("Dists found under {}, filtered by '{}': {}".format(self.base_url, crawler_filter.distro_filter, fdists))

        drel_repos = {}  # { '8': [RpmRepository(...),RpmRepository(...)] }
        for dist in fdists:
            drel = dist.lstrip('./')
            drel_repos.setdefault(drel, []).append(FlatcarRepository('{}{}'.format(base_url, drel)))
        return drel_repos

#        repos = []
#        for repo in self.get_mirrors(crawler_filter):
#            repos.extend(self.scan_repo(repo))
#        return repos
