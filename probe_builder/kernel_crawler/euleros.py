from . import repo
from . import rpm

def v2(ver):
    return ver.startswith('2')

class EulerOSMirror(repo.Distro):
    def get_mirrors(self, crawler_filter):
        mirrors = [
            # EulerOS 2
            # Lifecycle:
            # https://developer.huaweicloud.com/intl/en-us/euleros/lifecycle-management.html
            # Mirror list:
            # http://mirrors.huaweicloud.com/euler/
            rpm.RpmMirror('http://mirrors.huaweicloud.com/euler/', 'os/{}/'.format(crawler_filter.machine), v2),
            rpm.RpmMirror('http://mirrors.huaweicloud.com/euler/', 'updates/{}/'.format(crawler_filter.machine), v2),

        ]
        return mirrors
