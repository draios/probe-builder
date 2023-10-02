from __future__ import print_function
from concurrent.futures import ThreadPoolExecutor, as_completed

from collections import namedtuple
import click
import logging
import os
import sys

logger = logging.getLogger(__name__)

def machine2arch(mach):
    mach2arch = {
        'x86_64': 'amd64',
        'aarch64': 'arm64',
    }
    return mach2arch.get(mach, mach)

CrawlerFilter = namedtuple("CrawlerFilter", ["machine", "arch", "distro_filter", "kernel_filter"], defaults=[os.uname().machine, machine2arch(os.uname().machine), "", ""])

EMPTY_FILTER=CrawlerFilter()

# A repo.Repository is a collection of packages, implmemented through .get_package_tree()
#
# A repo.Mirror is a collection of repositories, returned by .list_repos()
#  TODO: should the Mirror be a subclass of Repository since it also implements get_package_tree?

# A repo.Distro is a collection of mirrors (and a subclass of mirror, so to be a drop-in replacement),
#   returned by .get_mirrors()
#   for which the list of repositories is just the union of all the repositories of each mirror

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

    # This is a compatibility layer for Mirror(s)/Distro(s) which
    # do not implement list_drel_repos
    def list_drel_repos(self, crawler_filter):
        return { "": self.list_repos(crawler_filter) }

    # The package tree of a mirror is simply the union of all the package trees of repos composing it
    def get_package_tree(self, crawler_filter):
        packages = {}
        drel_repos = self.list_drel_repos(crawler_filter)
        with click.progressbar(length=len(drel_repos), label='Listing packages', file=sys.stderr, item_show_func=to_s) as pbar:
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = { executor.submit(repo.get_package_tree, crawler_filter): (drel, str(repo)) for (drel, repos) in drel_repos.items() for repo in repos }
                for future in as_completed(futures):
                    drel, repo = futures[future]
                    for krel, dependencies in future.result().items():
                        packages.setdefault((drel, krel), set()).update(dependencies)
                    pbar.update(1, repo)  # Increments counter

        logger.info("Mirror.get_package_tree() returned packages with the following keys (packages omitted): {}".format(packages.keys()))
        return packages


class Distro(Mirror):

    def get_mirrors(self, crawler_filter):
        raise NotImplementedError

    # A distro (i.e. a collection of mirrors) will provide a set of repos
    # by composing (extending) all repos of each mirror, grouped by drel (distro release),
    # In other words, all kinetic* repos from each mirror will end up together
    def list_drel_repos(self, crawler_filter):
        # Merge the repositories obtained across the mirrors
        drel_repos = {}
        with click.progressbar(
                self.get_mirrors(crawler_filter), label='Checking mirrors of the distro', file=sys.stderr, item_show_func=to_s) as mirrors:
            for mirror in mirrors:
                _drel_repos = mirror.list_drel_repos(crawler_filter)
                for drel, repos in _drel_repos.items():
                    logger.info("drel '{}' has repos {} ".format(drel, repos))
                    drel_repos.setdefault(drel, []).extend(repos)

        return drel_repos
