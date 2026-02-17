import logging
import time
import yaml

logger = logging.getLogger(__name__)

class KernelCache:
    def __init__(self, cachefile):
        self.cachefile = cachefile
        self.load()

    def load(self):
        self.cache = {}
        yamldoc = None
        try:
            with open(self.cachefile, mode="rb") as fp:
                yamldoc = fp.read()
        except IOError:
            logger.warning("cache file {} not found".format(self.cachefile))
            return

        try:
            self.cache = yaml.load(yamldoc, Loader=yaml.FullLoader)
        except yaml.YAMLError as e:
            logger.warning("failed to parse cache file {}: {}".format(self.cachefile, e))

    def save(self):
        with open(self.cachefile, mode="w") as fp:
            yaml.dump(self.cache, fp, default_flow_style=False)
        logger.debug("cache saved to {}".format(self.cachefile))

    @staticmethod
    def make_key(kernel_type, machine, distro_filter, kernel_filter):
        # we use pipes (|) as separators to visually parse the key when looking at the cache file
        # other alternatives considered which would have worked anyway but would have been less visually clear were:
        # ":" would create discrepancies with the ":" used in YAML
        #     (entries with an empty last field i.e. kernel_filter would be quoted, others would not)
        # "-" might create confusion with the "-" used in kernel filter like "6.19.0-3-generic"
        return "{}|{}|{}|{}".format(kernel_type, machine, distro_filter, kernel_filter)

    def get(self, key, max_duration_hours):
        threshold = int(time.time()) - (max_duration_hours * 3600)
        if key in self.cache:
            entry = self.cache[key]
            if entry['ts'] > threshold:
                logger.debug("cache hit for key {}".format(key))
                return self.cache[key]["kernels"]
            else:
                logger.debug("cache entry {} expired".format(key))
                del self.cache[key]
                return None
        else:
            logger.debug("cache miss for key {}".format(key))
            return None

    def put(self, key, kernels):
        if key in self.cache:
            logger.debug("updating cache entry {}".format(key))
        else:
            logger.debug("adding cache entry {}".format(key))
        self.cache[key] = { "ts": int(time.time()), "kernels": kernels }

