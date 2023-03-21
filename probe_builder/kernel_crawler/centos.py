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
    def get_mirrors(self, crawler_filter):
        mirrors = [
            rpm.RpmMirror('http://mirror.centos.org/centos/', 'os/{}/'.format(crawler_filter.machine), v7_only),
            rpm.RpmMirror('http://mirror.centos.org/centos/', 'updates/{}/'.format(crawler_filter.machine), v7_only),
            # CentOS 8 reached end-of-life at the end of 2021, so no point looking for it
            # rpm.RpmMirror('http://mirror.centos.org/centos/', 'BaseOS/x86_64/os/', v8_only),
            rpm.RpmMirror('http://archive.kernel.org/centos-vault/', 'os/{}/'.format(crawler_filter.machine), v6_or_v7),
            rpm.RpmMirror('http://archive.kernel.org/centos-vault/', 'updates/{}/'.format(crawler_filter.machine), v6_or_v7),
            rpm.RpmMirror('http://archive.kernel.org/centos-vault/', 'BaseOS/{}/os/'.format(crawler_filter.machine), v8_only),
        ]
        return mirrors

class CentosStreamMirror(repo.Distro):
    def get_mirrors(self, crawler_filter):
        mirrors = [
            # CentOS 8 Stream
            rpm.RpmMirror('http://mirror.centos.org/centos/', 'BaseOS/{}/os/'.format(crawler_filter.machine), v8_stream),
            rpm.RpmMirror('http://mirror.centos.org/centos/', 'AppStream/{}/os/'.format(crawler_filter.machine), v8_stream),

            # CentOS 9 Stream
            rpm.RpmMirror('http://mirror.stream.centos.org/', 'BaseOS/{}/os/'.format(crawler_filter.machine), v9_only),
            rpm.RpmMirror('http://mirror.stream.centos.org/', 'AppStream/{}/os/'.format(crawler_filter.machine), v9_only),
        ]
        return mirrors
