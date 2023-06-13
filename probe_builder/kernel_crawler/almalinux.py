from . import repo
from . import rpm

def v8_only(ver):
    return ver.startswith('8')

def v9_only(ver):
    return ver.startswith('9')

class AlmaLinuxMirror(repo.Distro):
    def get_mirrors(self, crawler_filter):
        mirrors = [
            # AlmaLinux 8
            rpm.RpmMirror('http://repo.almalinux.org/almalinux/', 'BaseOS/{}/os/'.format(crawler_filter.machine), v8_only),
            rpm.RpmMirror('http://repo.almalinux.org/almalinux/', 'AppStream/{}/os/'.format(crawler_filter.machine), v8_only),
            # AlmaLinux 9
            rpm.RpmMirror('http://repo.almalinux.org/almalinux/', 'BaseOS/{}/os/'.format(crawler_filter.machine), v9_only),
            rpm.RpmMirror('http://repo.almalinux.org/almalinux/', 'AppStream/{}/os/'.format(crawler_filter.machine), v9_only),
        ]
        return mirrors
