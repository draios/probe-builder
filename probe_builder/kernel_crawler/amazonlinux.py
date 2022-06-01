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
    # Some distributions have a trailing slash (like AmazonLinux2022), some don't.
    return make_string(resp.splitlines()[0]).replace('$basearch', 'x86_64').rstrip('/') + '/'


class AmazonLinux1Mirror(repo.Distro):
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

    def __init__(self):
        super(AmazonLinux1Mirror, self).__init__([])

    def list_repos(self):
        repo_urls = set()
        with click.progressbar(
                self.AL1_REPOS, label='Checking repositories', file=sys.stderr, item_show_func=repo.to_s) as repos:
            for r in repos:
                repo_urls.add(get_al_repo("http://repo.us-east-1.amazonaws.com/", r))
        return [rpm.RpmRepository(url) for url in sorted(repo_urls)]


class AmazonLinux2Mirror(repo.Distro):
    AL2_REPOS = [
        'core/2.0',
        'core/latest',
        'extras/kernel-5.4/latest',
        'extras/kernel-5.10/latest',
    ]

    def __init__(self):
        super(AmazonLinux2Mirror, self).__init__([])

    def list_repos(self):
        repo_urls = set()
        with click.progressbar(
                self.AL2_REPOS, label='Checking repositories', file=sys.stderr, item_show_func=repo.to_s) as repos:
            for r in repos:
                repo_urls.add(get_al_repo("http://amazonlinux.us-east-1.amazonaws.com/2/", r + '/x86_64'))
        return [rpm.RpmRepository(url) for url in sorted(repo_urls)]

class AmazonLinux2022Mirror(repo.Distro):

    # This was obtained by running
    # docker run -it --rm amazonlinux:2022 python3 -c 'import dnf, json; db = dnf.dnf.Base(); print(json.dumps(db.conf.substitutions, indent=2))'
    AL2022_REPOS = [
        '2022.0.20220202',
        '2022.0.20220315',
        '2022.0.20220419',
        '2022.0.20220504',
    ]

    def __init__(self):
        super(AmazonLinux2022Mirror, self).__init__([])

    def list_repos(self):
        repo_urls = set()
        with click.progressbar(
                self.AL2022_REPOS, label='Checking repositories', file=sys.stderr, item_show_func=repo.to_s) as repos:
            # This was obtained by running:
            # cat /etc/yum.repos.d/amazonlinux.repo
            # https://al2022-repos-$awsregion-9761ab97.s3.dualstack.$awsregion.$awsdomain/core/mirrors/$releasever/$basearch/mirror.list
            for r in repos:
                repo_urls.add(get_al_repo("https://al2022-repos-us-east-1-9761ab97.s3.dualstack.us-east-1.amazonaws.com/core/mirrors/", r + '/x86_64'))
        return [rpm.RpmRepository(url) for url in sorted(repo_urls)]
