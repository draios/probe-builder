from __future__ import print_function
from concurrent.futures import ThreadPoolExecutor, as_completed

import click
import sys

class CrawlerFilter(object):
    def __init__(self, distro_filter='', kernel_filter=''):
        self.distro_filter = distro_filter
        self.kernel_filter = kernel_filter

EMPTY_FILTER=CrawlerFilter()

class Repository(object):
    def get_package_tree(self, crawler_filter):
        raise NotImplementedError

    def __str__(self):
        raise NotImplementedError


def to_s(s):
    if s is None:
        return ''
    return str(s)


class Mirror(object):

    def list_repos(self, crawler_filter):
        raise NotImplementedError

    def get_package_tree(self, crawler_filter):
        packages = {}
        repos = self.list_repos(crawler_filter)
        with click.progressbar(length=len(repos), label='Listing packages', file=sys.stderr, item_show_func=to_s) as pbar:
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = { executor.submit(repo.get_package_tree, crawler_filter): str(repo) for repo in repos }
                for future in as_completed(futures):
                    repo = futures[future]
                    for release, dependencies in future.result().items():
                        packages.setdefault(release, set()).update(dependencies)
                    pbar.update(1, repo)  # Increments counter
        return packages


class Distro(Mirror):
    def __init__(self, mirrors):
        super().__init__()
        self.mirrors = mirrors


    def list_repos(self, crawler_filter):
        repos = []
        with click.progressbar(
                self.mirrors, label='Checking repositories', file=sys.stderr, item_show_func=to_s) as mirrors:
            for mirror in mirrors:
                repos.extend(mirror.list_repos(crawler_filter))
        return repos
