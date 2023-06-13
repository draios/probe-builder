from . import repo
from . import rpm

def v8_only(ver):
    return ver.startswith('8')

def v9_only(ver):
    return ver.startswith('9')

class RockyLinuxMirror(repo.Distro):
    def get_mirrors(self, crawler_filter):
        mirrors = [
            # Rocky Linux 8
            rpm.RpmMirror('http://dl.rockylinux.org/pub/rocky/', 'BaseOS/{}/os/'.format(crawler_filter.machine), v8_only),
            rpm.RpmMirror('http://dl.rockylinux.org/pub/rocky/', 'AppStream/{}/os/'.format(crawler_filter.machine), v8_only),
            rpm.RpmMirror('http://dl.rockylinux.org/vault/rocky/', 'BaseOS/{}/os/'.format(crawler_filter.machine), v8_only),
            # Rocky Linux 9
            rpm.RpmMirror('http://dl.rockylinux.org/pub/rocky/', 'BaseOS/{}/os/'.format(crawler_filter.machine), v9_only),
            rpm.RpmMirror('http://dl.rockylinux.org/pub/rocky/', 'AppStream/{}/os/'.format(crawler_filter.machine), v9_only),
            # Valut repo not yet available for Rocky Linux 9
            #rpm.RpmMirror('http://dl.rockylinux.org/vault/rocky/', 'BaseOS/{}/os/'.format(crawler_filter.machine), v9_only),
        ]
        return mirrors