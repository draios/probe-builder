#!/usr/bin/env python
import sys

import click

from . import repo
from . import rpm
from probe_builder.kernel_crawler.download import get_url
from probe_builder.py23 import make_string


def get_al_repo(repo_root, repo_release):
    repo_pointer = repo_root + repo_release + "/mirror.list"
    resp = get_url(repo_pointer)
    # Some distributions have a trailing slash (like AmazonLinux2023), some don't.
    return make_string(resp.splitlines()[0]).rstrip('/') + '/'


class AmazonLinux1Mirror(repo.Mirror):
    AL1_REPOS = [
        'latest/updates',
        'latest/main',
        '2017.03/updates',
        '2017.03/main',
        '2017.09/updates',
        '2017.09/main',
        '2018.03/updates',
        '2018.03/main',
    ]

    def list_repos(self, crawler_filter):
        repo_urls = set()
        with click.progressbar(
                self.AL1_REPOS, label='Checking repositories', file=sys.stderr, item_show_func=repo.to_s) as repos:
            for r in repos:
                repo_urls.add(get_al_repo("http://repo.us-east-1.amazonaws.com/", r + '/' + crawler_filter.machine))
        return [rpm.RpmRepository(url) for url in sorted(repo_urls)]


class AmazonLinux2Mirror(repo.Mirror):
    AL2_REPOS = [
        'core/2.0',
        'core/latest',
        'extras/kernel-5.4/latest',
        'extras/kernel-5.10/latest',
        'extras/kernel-5.15/latest',
    ]

    def list_repos(self, crawler_filter):
        repo_urls = set()
        with click.progressbar(
                self.AL2_REPOS, label='Checking repositories', file=sys.stderr, item_show_func=repo.to_s) as repos:
            for r in repos:
                repo_urls.add(get_al_repo("http://amazonlinux.us-east-1.amazonaws.com/2/", r + '/' + crawler_filter.machine))
        return [rpm.RpmRepository(url) for url in sorted(repo_urls)]

class AmazonLinux2023Mirror(repo.Mirror):
    # NOTE: AL2022 was a preview release whose repos are no longer available.
    # This was obtained by running:
    # cat /etc/yum.repos.d/amazonlinux.repo
    #[amazonlinux]
    #name=Amazon Linux 2023 repository
    #mirrorlist=https://cdn.amazonlinux.com/al2023/core/mirrors/$releasever/$basearch/mirror.list
    #
    # NOTE: the "latest" release alone cumulatively provides kernel packages for all
    # previous releases, so there is no need to enumerate releases via core/releasemd.xml.
    AL2023_BASE_URL = "https://cdn.amazonlinux.com/al2023/core/mirrors/"
    AL2023_RELEASE = "latest"

    def list_repos(self, crawler_filter):
        repo_url = get_al_repo(self.AL2023_BASE_URL, self.AL2023_RELEASE + '/' + crawler_filter.machine)
        return [rpm.RpmRepository(repo_url)]
