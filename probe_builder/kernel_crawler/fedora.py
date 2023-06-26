from probe_builder.kernel_crawler import repo, rpm


def repo_filter(version):
    """Don't bother testing ancient versions"""
    try:
        return int(version.rstrip('/')) >= 32
    except ValueError:
        return False


class FedoraMirror(repo.Distro):
    def get_mirrors(self, crawler_filter):
        mirrors = [
            # Obtained by picking one from https://mirrors.fedoraproject.org/metalink?repo=fedora-37&arch=x86_64
            ### -> http://mirrors.rit.edu/fedora/fedora/linux/releases/37/Everything/x86_64/os/repodata/repomd.xml
            rpm.RpmMirror('http://mirrors.rit.edu/fedora/fedora/linux/releases/', 'Everything/{}/os/'.format(crawler_filter.machine), repo_filter),
            # https://mirrors.fedoraproject.org/metalink?repo=updates-released-f37&arch=x86_64
            ### -> http://mirrors.rit.edu/fedora/fedora/linux/updates/37/Everything/x86_64/repodata/repomd.xml
            rpm.RpmMirror('http://mirrors.rit.edu/fedora/fedora/linux/updates/', 'Everything/{}/'.format(crawler_filter.machine), repo_filter),
        ]
        return mirrors