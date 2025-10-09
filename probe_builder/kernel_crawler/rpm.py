#!/usr/bin/env python
from __future__ import print_function
import traceback

import logging
import requests
from lxml import etree, html
import sqlite3
import tempfile

from . import repo
from probe_builder.kernel_crawler.download import get_url
logger = logging.getLogger(__name__)

try:
    import lzma
except ImportError:
    from backports import lzma


class RpmRepository(repo.Repository):
    def __init__(self, base_url):
        self.base_url = base_url

    def __str__(self):
        return self.base_url

    @classmethod
    def get_loc_by_xpath(cls, text, expr):
        e = etree.fromstring(text)
        loc = e.xpath(expr, namespaces={
            'common': 'http://linux.duke.edu/metadata/common',
            'repo': 'http://linux.duke.edu/metadata/repo',
            'rpm': 'http://linux.duke.edu/metadata/rpm'
        })
        return loc[0]

    @classmethod
    def kernel_package_query(cls):
        # XXX kernel6.12 is needed by AmazonLinux 2023.7.20250331
        return '''name IN ('kernel', 'kernel6.12', 'kernel-devel', 'kernel6.12-devel') AND arch NOT IN ('src')'''

    @classmethod
    def build_base_query(cls, filter=''):
        base_query = '''SELECT version || '-' || release || '.' || arch, pkgkey FROM packages WHERE {}'''.format(
            cls.kernel_package_query())
        if not filter:
            return base_query, ()
        else:
            # if filtering, match anythint like 5.6.6 (version) or 5.6.6-300.fc32 (version || '-' || release)
            return base_query + ''' AND (version = ? OR version || '-' || "release" = ?)''', (filter, filter)

    @classmethod
    def parse_repo_db(cls, repo_db, filter='', origin_url='?'):
        db = sqlite3.connect(repo_db)
        cursor = db.cursor()

        base_query, args = cls.build_base_query(filter)
        query = '''WITH RECURSIVE transitive_deps(version, pkgkey) AS (
                {}
                UNION
                SELECT transitive_deps.version, provides.pkgkey
                    FROM provides
                    INNER JOIN requires USING (name, flags, epoch, version, "release")
                    INNER JOIN transitive_deps ON requires.pkgkey = transitive_deps.pkgkey
            ) SELECT transitive_deps.version, location_href FROM packages INNER JOIN transitive_deps using(pkgkey);
        '''.format(base_query)

        try:
            cursor.execute(query, args)
            return cursor.fetchall()
        except sqlite3.Error as e:
            raise ValueError("Error parsing repo db at {}: {}".format(origin_url, e))

    def get_repodb_url(self):
        repomd_url = self.base_url + 'repodata/repomd.xml'
        repomd = get_url(repomd_url)
        xpath_query = '//repo:repomd/repo:data[@type="primary_db"]/repo:location/@href'
        try:
            pkglist_url = self.get_loc_by_xpath(repomd, xpath_query)
        except IndexError:
            raise ValueError('Could resolve xpath query "{}" at {}'.format(xpath_query, repomd_url))
        return self.base_url + pkglist_url

    def get_package_tree(self, crawler_filter):
        packages = {}
        try:
            repodb_url = self.get_repodb_url()
            repodb = get_url(repodb_url)
        except (requests.exceptions.RequestException, ValueError):
            traceback.print_exc()
            return {}
        with tempfile.NamedTemporaryFile() as tf:
            tf.write(repodb)
            tf.flush()
            for pkg in self.parse_repo_db(tf.name, crawler_filter.kernel_filter, repodb_url):
                version, url = pkg
                packages.setdefault(version, set()).add(self.base_url + url)
        return packages


class RpmMirror(repo.Mirror):

    def __init__(self, base_url, variant, repo_filter=None):
        self.base_url = base_url
        self.variant = variant
        if repo_filter is None:
            repo_filter = lambda _: True
        self.repo_filter = repo_filter

    def __str__(self):
        return self.base_url

    def dist_url(self, dist):
        return '{}{}{}'.format(self.base_url, dist, self.variant)

    def dist_exists(self, dist):
        try:
            r = requests.get(self.dist_url(dist))
            r.raise_for_status()
        except requests.exceptions.RequestException:
            return False
        return True

    def list_drel_repos(self, crawler_filter):
        dists = requests.get(self.base_url)
        dists.raise_for_status()
        dists = dists.content
        doc = html.fromstring(dists, self.base_url)
        dists = doc.xpath('/html/body//a[not(@href="../")]/@href')

        # On 2025-10-09 Almalinux started adding ./ prefix to all paths -- remove it if present
        dists = [d[2:] if d.startswith('./') else d for d in dists]

        fdists = [dist for dist in dists
                if dist.endswith('/')
                and not dist.startswith('/')
                and not dist.startswith('?')
                and not dist.startswith('http')
                and self.repo_filter(dist)
                and self.dist_exists(dist)
                and dist.startswith(crawler_filter.distro_filter)
                ]

        logger.info("Dists found under {}, filtered by '{}': {}".format(self.base_url, crawler_filter.distro_filter, fdists))

        # Grouped dists
        drel_repos = {}  # { '8': [RpmRepository(...),RpmRepository(...)] }
        for dist in fdists:
            # First, remove "/" suffix, if any
            # Then, remove .x suffix, if any so that 8, 8.1, 8.2 all end up under '8' (which is normally an alias for the latest 8.x)
            # This way, we avoid crawling the latest 8.x twice (once for "8" and once for "8.x")
            drel = dist.split('/',1)[0].split('.',1)[0]
            drel_repos.setdefault(drel, []).append(RpmRepository(self.dist_url(dist)))

        return drel_repos
