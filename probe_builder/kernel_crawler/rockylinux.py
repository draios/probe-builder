from . import repo
from . import rpm

def v8_only(ver):
    return ver.startswith('8')

def v9_only(ver):
    return ver.startswith('9')

class RockyLinuxMirror(repo.Distro):
    def __init__(self):
        mirrors = [
            # Rocky Linux 8
            rpm.RpmMirror('http://dl.rockylinux.org/pub/rocky/', 'BaseOS/x86_64/os/', v8_only),
            rpm.RpmMirror('http://dl.rockylinux.org/pub/rocky/', 'AppStream/x86_64/os/', v8_only),
            rpm.RpmMirror('http://dl.rockylinux.org/vault/rocky/', 'BaseOS/x86_64/os/', v8_only),
            # Rocky Linux 9
            rpm.RpmMirror('http://dl.rockylinux.org/pub/rocky/', 'BaseOS/x86_64/os/', v9_only),
            rpm.RpmMirror('http://dl.rockylinux.org/pub/rocky/', 'AppStream/x86_64/os/', v9_only),
            # Valut repo not yet available for Rocky Linux 9
            #rpm.RpmMirror('http://dl.rockylinux.org/vault/rocky/', 'BaseOS/x86_64/os/', v9_only),
        ]
        super(RockyLinuxMirror, self).__init__(mirrors)
