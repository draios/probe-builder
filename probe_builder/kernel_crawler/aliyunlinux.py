from . import repo
from . import rpm

def v2_or_v3(ver):
    return ver.startswith('2') or ver.startswith('3')

class AliyunLinuxMirror(repo.Distro):
    def get_mirrors(self, crawler_filter):
        mirrors = [
            # AliyunLinux 2 and 3
            # Mirror list on cloud-init config example:
            # https://www.alibabacloud.com/help/en/elastic-compute-service/latest/use-alibaba-cloud-linux-2-images-in-an-on-premises-environment
            # https://www.alibabacloud.com/help/en/elastic-compute-service/latest/use-alibaba-cloud-linux-3-images-in-an-on-premises-environment
            rpm.RpmMirror('http://mirrors.aliyun.com/alinux/', 'os/{}/'.format(crawler_filter.machine), v2_or_v3),
            rpm.RpmMirror('http://mirrors.aliyun.com/alinux/', 'updates/{}/'.format(crawler_filter.machine), v2_or_v3),
            rpm.RpmMirror('http://mirrors.aliyun.com/alinux/', 'plus/{}/'.format(crawler_filter.machine), v2_or_v3),

        ]
        return mirrors
