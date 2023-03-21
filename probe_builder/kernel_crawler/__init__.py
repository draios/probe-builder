from .almalinux import AlmaLinuxMirror
from .amazonlinux import AmazonLinux1Mirror, AmazonLinux2Mirror, AmazonLinux2022Mirror
from .centos import CentosMirror, CentosStreamMirror
from .fedora import FedoraMirror
from .oracle import Oracle6Mirror, Oracle7Mirror, Oracle8Mirror, Oracle9Mirror
from .photon_os import PhotonOsMirror
from .rockylinux import RockyLinuxMirror

from .debian import DebianMirror
from .ubuntu import UbuntuMirror

from .flatcar import FlatcarMirror

DISTROS = {
    'AlmaLinux': AlmaLinuxMirror,
    'AmazonLinux': AmazonLinux1Mirror,
    'AmazonLinux2': AmazonLinux2Mirror,
    'AmazonLinux2022': AmazonLinux2022Mirror,
    'CentOS': CentosMirror,
    'CentOSStream': CentosStreamMirror,
    'Fedora': FedoraMirror,
    'Oracle6': Oracle6Mirror,
    'Oracle7': Oracle7Mirror,
    'Oracle8': Oracle8Mirror,
    'Oracle9': Oracle9Mirror,
    'PhotonOS': PhotonOsMirror,
    'RockyLinux': RockyLinuxMirror,

    'Debian': DebianMirror,
    'Ubuntu': UbuntuMirror,

    'Flatcar': FlatcarMirror,
}


def crawl_kernels(distro, distro_filter='', kernel_filter=''):
    dist = DISTROS[distro]()
    dist.set_distro_filter(distro_filter)
    pt = dist.get_package_tree(kernel_filter)
    dist.set_distro_filter('')
    return pt
