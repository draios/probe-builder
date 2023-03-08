from . import repo
from . import rpm

def v7_only(ver):
    return ver.startswith('7')

def v8_only(ver):
    return ver.startswith('8')

def v8_stream(ver):
    return ver.startswith('8-stream')

def v9_only(ver):
    return ver.startswith('9')

def v6_or_v7(ver):
    return ver.startswith('6') or ver.startswith('7')

class CentosMirror(repo.Distro):
    def __init__(self):
        mirrors = [
            rpm.RpmMirror('http://mirror.centos.org/centos/', 'os/x86_64/', v7_only),
            rpm.RpmMirror('http://mirror.centos.org/centos/', 'updates/x86_64/', v7_only),
            # CentOS 8 reached end-of-life at the end of 2021, so no point looking for it
            # rpm.RpmMirror('http://mirror.centos.org/centos/', 'BaseOS/x86_64/os/', v8_only),
            rpm.RpmMirror('http://linuxsoft.cern.ch/centos-vault/', 'os/x86_64/', v6_or_v7),
            rpm.RpmMirror('http://linuxsoft.cern.ch/centos-vault/', 'updates/x86_64/', v6_or_v7),
            rpm.RpmMirror('http://linuxsoft.cern.ch/centos-vault/', 'BaseOS/x86_64/os/', v8_only),
        ]
        super(CentosMirror, self).__init__(mirrors)

class CentosStreamMirror(repo.Distro):
    def __init__(self):
        mirrors = [
            # CentOS 8 Stream
            rpm.RpmMirror('http://mirror.centos.org/centos/', 'BaseOS/x86_64/os/', v8_stream),
            rpm.RpmMirror('http://mirror.centos.org/centos/', 'AppStream/x86_64/os/', v8_stream),

            # CentOS 9 Stream
            rpm.RpmMirror('http://mirror.stream.centos.org/', 'BaseOS/x86_64/os/', v9_only),
            rpm.RpmMirror('http://mirror.stream.centos.org/', 'AppStream/x86_64/os/', v9_only),
        ]
        super(CentosStreamMirror, self).__init__(mirrors)
