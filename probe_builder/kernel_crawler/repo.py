from __future__ import print_function

import click
import sys


class Repository(object):
    def get_package_tree(self, kernel_filter=''):
        raise NotImplementedError

    def __str__(self):
        raise NotImplementedError


def to_s(s):
    if s is None:
        return ''
    return str(s)


class Mirror(object):

    distro_filter=''
    def list_repos(self):
        raise NotImplementedError

    def __init__(self):
        self.distro_filter = ''

    def set_distro_filter(self, distro_filter):
        self.distro_filter=distro_filter

    def get_package_tree(self, kernel_filter=''):
        packages = {}
        repos = self.list_repos()
        with click.progressbar(repos, label='Listing packages', file=sys.stderr, item_show_func=to_s) as repos:
            for repo in repos:
                for release, dependencies in repo.get_package_tree(kernel_filter).items():
                    packages.setdefault(release, set()).update(dependencies)
        return packages


class Distro(Mirror):
    def __init__(self, mirrors):
        super().__init__()
        self.mirrors = mirrors


    def list_repos(self):
        repos = []
        with click.progressbar(
                self.mirrors, label='Checking repositories', file=sys.stderr, item_show_func=to_s) as mirrors:
            for mirror in mirrors:
                mirror.set_distro_filter(self.distro_filter)
                repos.extend(mirror.list_repos())
                mirror.set_distro_filter('')
        return repos
