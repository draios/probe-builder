import os

import requests
from lxml import html

from probe_builder.kernel_crawler.repo import Repository, Mirror


class FlatcarRepository(Repository):
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


class FlatcarMirror(Mirror):
    CHANNELS = ['stable', 'beta', 'alpha']

    def get_mirrors(self, crawler_filter):
        mirrors = ['https://{}.release.flatcar-linux.net/{}-usr/'.format(channel, crawler_filter.arch) for channel in self.CHANNELS]
        return mirrors

    def scan_repo(self, base_url):
        dists = requests.get(base_url)
        dists.raise_for_status()
        dists = dists.content
        doc = html.fromstring(dists, base_url)
        dists = doc.xpath('/html/body//a[not(@href="../")]/@href')
        return [FlatcarRepository('{}{}'.format(base_url, dist.lstrip('./'))) for dist in dists
                if dist.endswith('/')
                and dist.startswith('./')
                and 'current' not in dist
                and '-' not in dist
                ]

    def list_repos(self, crawler_filter):
        repos = []
        for repo in self.get_mirrors(crawler_filter):
            repos.extend(self.scan_repo(repo))
        return repos
