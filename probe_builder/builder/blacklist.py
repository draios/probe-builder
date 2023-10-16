import jinja2
import logging
import re
import sys
import yaml

logger = logging.getLogger(__name__)

class KernelBlacklist:
    def __init__(self, yamldoc, probe_version):
        self.matchers = {}
        self.blacklist = []
        if yamldoc:
            config = yaml.safe_load(yamldoc)
            for mn, mv in config['matchers'].items():
                mv = re.compile(mv)
                self.matchers[mn] = mv
            self.blacklist = config['blacklists']
        self.probe_version = probe_version

    def blacklist_reason(self, probe_kind, kernel_release):
        logger.debug("======== {} probe {} kernel {}".format(probe_kind, self.probe_version, kernel_release))
        for b in self.blacklist:
            logger.debug("==== evaluating blacklist entry {}".format(b['description']))
            if self.probe_version in b['probe_versions']:
                logger.debug("probe version {} matches one of agent versions {}".format(self.probe_version, b['probe_versions']))
            else:
                logger.debug("probe version {} NOT in {}".format(self.probe_version, b['probe_versions']))
                continue

            if not b['probe_kinds'] or probe_kind in b['probe_kinds']:
                logger.debug("probe kind {} matches one of {}".format(probe_kind, b['probe_kinds']))
            else:
                logger.debug("probe kind {} does NOT match one of {}".format(probe_kind, b['probe_kinds']))
                continue

            m = self.matchers[b['matcher']].search(kernel_release)
            if m:
                logger.debug("kernel {} matches matcher {}".format(kernel_release, b['matcher']))
                logger.debug("unpack result: {}".format(m.groupdict()))
                sif = b['skip_if']
                t = jinja2.Template(sif)
                r = t.render(m.groupdict())
                if r and r != "False":
                    logger.debug("== Blacklisted by {}, eval returned {}({})".format(b['description'], r, type(r)))
                    return b['description']
            else:
                logger.debug("kernel {} does NOT belong to matcher {}".format(kernel_release, b['matcher']))

        logger.debug("== kernel NOT blacklisted")
        return None


## =========== Test code =============
_test_blacklist = """\
matchers:
  redhat: ^(?P<version>[0-9]\.[0-9]+\.[0-9]+)-(?P<rpmrelver>[0-9]+)(?P<rpmrelpatch>(\.[0-9]+)*)\.(?P<rhel>el.*)\.(?P<arch>[a-z0-9-_]+)$
  generic: ^(?P<major>[0-9])\.(?P<minor>[0-9]+)\..*

blacklists:
  - description: "4.18.0 RHEL kernels with release version under 500"
    probe_versions: [ 12.16.0, 12.16.1, 12.16.2, 12.16.3, 12.17.0 ]
    probe_kinds: [ kmod ]
    matcher: redhat
    skip_if: "{{ (version == '4.18.0' and (rpmrelver|int)<=500) }}"

  - description: "6.2 kernel build"
    probe_versions: [ 12.12.0 ]
    probe_kinds: [ kmod ]
    matcher: generic
    skip_if: "{{ major|int >= 6 or major|int == 6 and minor|int >= 2 }}"
"""

if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    kbl = KernelBlacklist(_test_blacklist, "12.16.3")
    assert kbl.blacklist_reason("kmod", "4.18.0-497.el8.x86_64")
    assert not kbl.blacklist_reason("kmod", "4.18.0-506.el8.x86_64")
    assert not kbl.blacklist_reason("kmod", "6.2.0")
    kbl = KernelBlacklist(_test_blacklist, "12.12.0")
    assert kbl.blacklist_reason("kmod", "6.2.0")
    assert kbl.blacklist_reason("kmod", "7.0.0")
