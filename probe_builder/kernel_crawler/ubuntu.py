from . import deb
from . import repo


class UbuntuMirror(repo.Distro):
    def get_mirrors(self, crawler_filter):
        mirrors = [
            deb.DebMirror('http://mirrors.edge.kernel.org/ubuntu/'),
            deb.DebMirror('http://security.ubuntu.com/ubuntu/'),
        ]
        return mirrors
