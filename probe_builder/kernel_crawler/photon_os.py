from . import rpm
from . import repo


class PhotonOsRepository(rpm.RpmRepository):
    @classmethod
    def kernel_package_query(cls):
        # We exclude `esx` kernels because they don't support CONFIG_TRACEPOINTS,
        # see https://github.com/vmware/photon/issues/1223.
        # We also exclude all the other variants for now (plus Linux-PAM-devel).
        return '''(
            (name = 'linux' OR name LIKE 'linux-%devel%')
            AND name NOT LIKE '%-PAM-%'
            AND name NOT LIKE '%-esx-%'
            AND name NOT LIKE '%-rt-%'
            AND name NOT LIKE '%-secure-%'
            AND name NOT LIKE '%-aws-%'
        )
        '''


class PhotonOsMirror(repo.Distro):
    PHOTON_OS_VERSIONS = [
        ('3.0', '_release'),
        ('3.0', '_updates'),
        ('4.0', ''),
        ('4.0', '_release'),
        ('4.0', '_updates'),
    ]

    def __init__(self):
        super(PhotonOsMirror, self).__init__([])

    def list_repos(self, crawler_filter):
        return [
            PhotonOsRepository('https://packages.vmware.com/photon/{v}/photon{r}_{v}_x86_64/'.format(
                v=version, r=repo_tag))
            for version, repo_tag in self.PHOTON_OS_VERSIONS]
