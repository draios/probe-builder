from . import repo
from . import deb
import click
import sys


def repo_filter(dist):
    return 'stable' not in dist and 'testing' not in dist and not dist.startswith('Debian')


class DebianMirror(repo.Distro):
    def get_mirrors(self, crawler_filter):
        mirrors = [
            deb.DebMirror('http://mirrors.edge.kernel.org/debian/', repo_filter),
            deb.DebMirror('http://security.debian.org/', repo_filter),
        ]
        return mirrors

    # For Debian mirrors, we need to override this method so that dependencies
    # can be resolved (i.e. build_package_tree) across multiple repositories.
    # This is namely required for the linux-kbuild package, which is typically
    # hosted on a different repository compared to the kernel packages
    # In particular, we get all DebRepository'es for a given distro release
    # (e.g. for bookworm we'll have bookwork, bookworm-backports, bookworm-proposed-updates etc...)
    # and resolve dependencies across those.
    # At the end, we return a dictionary: { (drel, krel) : [...] }
    def get_package_tree(self, crawler_filter):
        packages = {}
        drel_repos = self.list_drel_repos(crawler_filter)
        with click.progressbar(drel_repos.items(), label='Listing packages', file=sys.stderr, item_show_func=repo.to_s) as drel_repos_items:
            for drel, repos in drel_repos_items:
                all_packages = {}
                all_kernel_packages = []
                for repository in repos:
                    repo_packages = repository.get_raw_package_db()
                    all_packages.update(repo_packages)
                    kernel_packages = repository.get_package_list(repo_packages, crawler_filter.kernel_filter)
                    all_kernel_packages.extend(kernel_packages)
                for krel, dependencies in deb.DebRepository.build_package_tree(all_packages, all_kernel_packages).items():
                    packages.setdefault((drel, krel), set()).update(dependencies)
        return packages
