#!/usr/bin/env python
import sys

import click

from . import repo
from . import rpm
from lxml import etree, html
import requests
from probe_builder.kernel_crawler.download import get_url
from probe_builder.py23 import make_string


def get_al_repo(repo_root, repo_release):
    repo_pointer = repo_root + repo_release + "/mirror.list"
    resp = get_url(repo_pointer)
    # Some distributions have a trailing slash (like AmazonLinux2022), some don't.
    return make_string(resp.splitlines()[0]).rstrip('/') + '/'


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

    def list_repos(self, crawler_filter):
        repo_urls = set()
        with click.progressbar(
                self.AL1_REPOS, label='Checking repositories', file=sys.stderr, item_show_func=repo.to_s) as repos:
            for r in repos:
                repo_urls.add(get_al_repo("http://repo.us-east-1.amazonaws.com/", r + '/' + crawler_filter.machine))
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

    def list_repos(self, crawler_filter):
        repo_urls = set()
        with click.progressbar(
                self.AL2_REPOS, label='Checking repositories', file=sys.stderr, item_show_func=repo.to_s) as repos:
            for r in repos:
                repo_urls.add(get_al_repo("http://amazonlinux.us-east-1.amazonaws.com/2/", r + '/' + crawler_filter.machine))
        return [rpm.RpmRepository(url) for url in sorted(repo_urls)]

class AmazonLinux2022Mirror(repo.Distro):

    # This was obtained by running
    # docker run -it --rm amazonlinux:2022 python3 -c 'import dnf, json; db = dnf.dnf.Base(); print(json.dumps(db.conf.substitutions, indent=2))'
    # NOTE: This has been deprecated in favor of dynamic release discovery
    #AL2022_REPOS = [
    #    '2022.0.20220202',
    #    '2022.0.20220315',
    #    '2022.0.20220419',
    #    '2022.0.20220504',
    #]

    # This was obtained by running:
    # cat /etc/yum.repos.d/amazonlinux.repo
    # https://al2022-repos-$awsregion-9761ab97.s3.dualstack.$awsregion.$awsdomain/core/mirrors/$releasever/$basearch/mirror.list
    #AL2022_BASE_URL = "https://al2022-repos-us-east-1-9761ab97.s3.dualstack.us-east-1.amazonaws.com"

    # cat /etc/yum.repos.d/amazonlinux.repo
    #[amazonlinux]
    #name=Amazon Linux 2023 repository
    #mirrorlist=https://cdn.amazonlinux.com/al2023/core/mirrors/$releasever/$basearch/mirror.list

    AL202X_BASE_URLS = ["https://cdn.amazonlinux.com/al2022", "https://cdn.amazonlinux.com/al2023"]

    def __init__(self):
        super(AmazonLinux2022Mirror, self).__init__([])

    def list_repos(self, crawler_filter):
        repos = []
        for base_url in self.AL202X_BASE_URLS:
            repos.extend(self.list_repos_for_url(base_url=base_url, crawler_filter=crawler_filter))
        return repos

    def list_repos_for_url(self, base_url, crawler_filter):
        # List of all available releases
        releasemd_url = "{}/{}".format(base_url, "core/releasemd.xml")
        releasemd_xml = get_url(releasemd_url)
        e = etree.fromstring(releasemd_xml)
        # see https://github.com/aws/amazon-ecs-ami/blob/main/generate-release-vars.sh
        # NOTE: the latest release alone seems to cumulatively provide kernel packages
        # for all previous releases, too. Hence the last() bit.
        expr = "//root/releases/release[last()]/@version"

        # However, if you ever need to list ALL releases, use the following expression instead
        #expr = "//root/releases/release/@version"

        releases = e.xpath(expr)

        # NOTE: if you need to fall back to the previous, manually-generated list of releases
        # uncomment the following line:
        #releases = self.AL2022_REPOS

        repo_urls = set()
        with click.progressbar(
                releases, label='Checking repositories', file=sys.stderr, item_show_func=repo.to_s) as repos:

            for r in repos:
                try:
                    print("Adding repo {}".format(r), flush=True)
                    repo_url = get_al_repo(
                        "{}/{}".format(base_url, "core/mirrors/"),
                        r + '/' + crawler_filter.machine
                    )
                    repo_urls.add(repo_url)
                except requests.exceptions.HTTPError as err:
                    print("WARNING: Could not get data for AmazonLinux202x base_url: {}, release: {}. Got error: {}".format(base_url, r, err), flush=True)

        return [rpm.RpmRepository(url) for url in sorted(repo_urls)]
