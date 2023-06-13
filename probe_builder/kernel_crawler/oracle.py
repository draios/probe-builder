from . import repo
from . import rpm


class OracleRepository(rpm.RpmRepository):
    @classmethod
    def kernel_package_query(cls):
        # here we want to filter out kernel source packages, so we accept both x86_64 and aarch64
        # --> at the end of the day, they're separate repositories so we only expect to find
        # the ones matching the architecture of the repository
        return '''(name IN ('kernel', 'kernel-devel', 'kernel-uek', 'kernel-uek-devel') AND arch IN ('x86_64', 'aarch64'))'''


class Oracle6Mirror(repo.Distro):
    OL6_REPOS = [
        'http://yum.oracle.com/repo/OracleLinux/OL6/latest/{}/',
        'http://yum.oracle.com/repo/OracleLinux/OL6/MODRHCK/{}/',
        'http://yum.oracle.com/repo/OracleLinux/OL6/UEKR4/{}/',
        'http://yum.oracle.com/repo/OracleLinux/OL6/UEKR3/latest/{}/',
        'http://yum.oracle.com/repo/OracleLinux/OL6/UEK/latest/{}/',
    ]

    def list_repos(self, crawler_filter):
        return [OracleRepository(url.format(crawler_filter.machine)) for url in self.OL6_REPOS]


class Oracle7Mirror(repo.Distro):
    OL7_REPOS = [
        'http://yum.oracle.com/repo/OracleLinux/OL7/latest/{}/',
        'http://yum.oracle.com/repo/OracleLinux/OL7/MODRHCK/{}/',
        'http://yum.oracle.com/repo/OracleLinux/OL7/UEKR6/{}/',
        'http://yum.oracle.com/repo/OracleLinux/OL7/UEKR5/{}/',
        'http://yum.oracle.com/repo/OracleLinux/OL7/UEKR4/{}/',
        'http://yum.oracle.com/repo/OracleLinux/OL7/UEKR3/{}/',
    ]

    def list_repos(self, crawler_filter):
        return [OracleRepository(url.format(crawler_filter.machine)) for url in self.OL7_REPOS]


class Oracle8Mirror(repo.Distro):
    OL8_REPOS = [
        'http://yum.oracle.com/repo/OracleLinux/OL8/baseos/latest/{}/',
        'http://yum.oracle.com/repo/OracleLinux/OL8/UEKR6/{}/',
        'http://yum.oracle.com/repo/OracleLinux/OL8/UEKR7/{}/',
    ]

    def list_repos(self, crawler_filter):
        return [OracleRepository(url.format(crawler_filter.machine)) for url in self.OL8_REPOS]


class Oracle9Mirror(repo.Distro):
    OL9_REPOS = [
        'http://yum.oracle.com/repo/OracleLinux/OL9/baseos/latest/{}/',
        'http://yum.oracle.com/repo/OracleLinux/OL9/appstream/{}/',
        'http://yum.oracle.com/repo/OracleLinux/OL9/UEKR7/{}/',
    ]

    def list_repos(self, crawler_filter):
        return [OracleRepository(url.format(crawler_filter.machine)) for url in self.OL9_REPOS]
