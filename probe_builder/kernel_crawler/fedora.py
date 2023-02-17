from probe_builder.kernel_crawler import repo, rpm


def repo_filter(version):
    """Don't bother testing ancient versions"""
    try:
        return int(version.rstrip('/')) >= 32
    except ValueError:
        return False


class FedoraMirror(repo.Distro):
    def __init__(self):
        mirrors = [
            # Obtained by picking one from https://mirrors.fedoraproject.org/metalink?repo=fedora-37&arch=x86_64
            ### -> http://download-ib01.fedoraproject.org/pub/fedora/linux/releases/37/Everything/x86_64/os/repodata/repomd.xml
            rpm.RpmMirror('http://download-ib01.fedoraproject.org/pub/fedora/linux/releases/', 'Everything/x86_64/os/', repo_filter),
            # https://mirrors.fedoraproject.org/metalink?repo=updates-released-f37&arch=x86_64
            ### -> http://download-ib01.fedoraproject.org/pub/fedora/linux/updates/37/Everything/x86_64/repodata/repomd.xml
            rpm.RpmMirror('http://download-ib01.fedoraproject.org/pub/fedora/linux/updates/', 'Everything/x86_64/', repo_filter),
        ]
        super(FedoraMirror, self).__init__(mirrors)


