from . import repo
from . import rpm

def v8_only(ver):
    return ver.startswith('8')

def v9_only(ver):
    return ver.startswith('9')

class AlmaLinuxMirror(repo.Distro):
    def __init__(self):
        mirrors = [
            # AlmaLinux 8
            rpm.RpmMirror('http://repo.almalinux.org/almalinux/', 'BaseOS/x86_64/os/', v8_only),
            rpm.RpmMirror('http://repo.almalinux.org/almalinux/', 'AppStream/x86_64/os/', v8_only),
            # AlmaLinux 9
            rpm.RpmMirror('http://repo.almalinux.org/almalinux/', 'BaseOS/x86_64/os/', v9_only),
            rpm.RpmMirror('http://repo.almalinux.org/almalinux/', 'AppStream/x86_64/os/', v9_only),
        ]
        super(AlmaLinuxMirror, self).__init__(mirrors)
