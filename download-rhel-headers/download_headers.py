#!/usr/bin/env python3
from redhat_auth import RedHatTokenAuth
from artifactory import ArtifactoryHelper
import os
import hashlib
import requests
import sys
import time
import re
import argparse

RHAPI_BASE_URL = "https://api.access.redhat.com/management/v1"
DEFAULT_RPM_BUCKETS = [
    "rhel-8-for-x86_64-baseos-rpms",
    "rhel-8-for-x86_64-baseos-eus-rpms",
    "rhocp-4.7-for-rhel-8-x86_64-rpms",
]

PKG_REGEXP = "kernel-(core|devel)"

ARTIFACTORY_BUCKET = "redhat-sources"

MAX_RETRIES = 10
MAX_REDIRECTS = 10


def log(str):
    if not args.quiet:
        print(str)


def dbg(str):
    if args.verbose:
        print(str)


def pkg_name(pkg):
    if not pkg:
        return ""
    return "{name}-{version}-{release}.{arch}.rpm".format(**pkg)


def https_download_file(auth, url, ofname, accept="application/octet-stream", exp_sha256=None):
    # Download file into memory
    s = requests.Session()
    s.max_redirects = MAX_REDIRECTS
    headers = {"accept": accept}
    response = s.get(url=url, headers=headers, auth=auth)
    response.raise_for_status()

    # Check the received SHA-256 against the expected one
    data = response.content
    actual_hash = hashlib.sha256(data).hexdigest()
    if actual_hash != exp_sha256:
        raise Exception("Hash mismatch!")

    # Write data to file on disk
    with open(ofname, "wb") as f:
        f.write(data)

    return response


parser = argparse.ArgumentParser()
parser.add_argument("-t", "--redhat-token", help="RedHat token", required=True)
parser.add_argument(
    "-b", "--redhat-bucket", dest="buckets", action="append", default=[], help="Redhat bucket(s) to scrape"
)
parser.add_argument("-a", "--artifactory-server", help="Artifactory server")
parser.add_argument("-A", "--artifactory-key", help="Artifactory API key")
parser.add_argument("-q", "--quiet", action="store_true")
parser.add_argument("-v", "--verbose", action="store_true")
parser.add_argument("-o", "--outdir", help="Output directory", default=".")

args = parser.parse_args()
if not args.buckets:
    args.buckets = DEFAULT_RPM_BUCKETS

# print(args)

redhat_auth = RedHatTokenAuth(args.redhat_token)

art_helper = None
if args.artifactory_server and args.artifactory_key:
    base_url = "https://{artifactory_server}/artifactory".format(artifactory_server=args.artifactory_server)
    art_helper = ArtifactoryHelper(base_url=base_url, bucket=ARTIFACTORY_BUCKET, apikey=args.artifactory_key)

packages = {}
s = requests.Session()

for bucket in args.buckets:
    print(bucket, end="")
    # There's no search API, so walk every single package in the repository
    done = False
    offset = 0
    retries = 0
    while not done:
        # I know about f-strings, I just don't like symbols being buried in strings, call me old-style
        url = "{RHAPI_BASE_URL}/packages/cset/{bucket}/arch/x86_64".format(
            RHAPI_BASE_URL=RHAPI_BASE_URL, bucket=bucket
        )
        params = {"limit": 100, "offset": offset}

        headers = {"accept": "application/json"}
        response = s.get(url, headers=headers, params=params, auth=redhat_auth)
        response.raise_for_status()
        # print (response.body)
        j = response.json()
        # print(j)
        # The RH API server sometimes faceplants for unknown reasons. Sleep, then retry
        if j.get("error"):
            retries += 1
            msg = "Encountered error {}: {}. ".format(j["error"]["code"], {j["error"]["message"]})
            if retries < MAX_RETRIES:
                log(msg + "Attempting retry")
                time.sleep(5)
                continue
            else:
                log(msg + "Aborting")
                sys.exit(-2)

        # Determine whether we need to keep going or if we're at the end of the package list
        pag = j["pagination"]
        if not pag:
            sys.exit("Got mal-formed JSON response:" + j)

        if pag["count"] < pag["limit"]:
            done = True  # terminate
        else:
            offset += pag["limit"]

        # Search through the package list to see if it contains any we care about
        pkgs = j["body"]
        for p in pkgs:
            # skip files we're not interested in
            if not re.match(PKG_REGEXP, p["name"]):
                continue
            # build rpm name from the data received from the server
            pname = pkg_name(p)
            # REMOVEME
            # pname += "DELETEME." + pname
            # add {pkg.rpm: url, sha256} to map
            packages[pname] = {"url": p["downloadHref"], "sha256": p["checksum"]}

        # Print a little status update so it doesn't look like we've gone out to lunch
        print(".", end="")
        sys.stdout.flush()
    print("")
    # end of while not done

    # Diff the list with what's already in artifactory and only keep the delta
    if art_helper:
        # get a dictionary of RPMs -> SHA256 already present in artifactory
        art_list = art_helper.list_artifacts()
        # try to remove them if present in our list
        for rpm, sha256 in art_list.items():
            if rpm in packages:
                # check SHA
                if packages[rpm]["sha256"] != sha256:
                    log("{rpm} is already in artifactory, but sha256's do not match!".format(rpm=rpm))
                else:
                    del packages[rpm]
                    dbg("{rpm} is already in artifactory and is identical, pruning it".format(rpm=rpm))

    # Download packages, unless already present in local filesystem
    outdir = args.outdir
    for pn, pkg in packages.items():
        fn = os.path.join(args.outdir, pn)
        do_download = True
        if os.path.exists(fn):
            with open(fn, "rb") as f:
                bytes = f.read()  # read entire file as bytes
                readable_hash = hashlib.sha256(bytes).hexdigest()
                if readable_hash != pkg["sha256"]:
                    # We already downloaded the file, but it changed on the server
                    log("A local {fn} exists but checksums differ. Deleting local and redownloading".format(fn=fn))
                    os.unlink(fn)
                else:
                    dbg("A local {fn} exists and checksums match, so it will not be downloaded.".format(fn=fn))
                    do_download = False

        if do_download:
            num_retries = 0
            log("Downloading {}".format(pn))
            # We need to retry because sometimes the download server has a sulk
            while num_retries < MAX_RETRIES:
                try:
                    resp = https_download_file(auth=redhat_auth, url=pkg["url"], ofname=fn, exp_sha256=pkg["sha256"])
                    log("Success")
                    break
                except requests.exceptions.HTTPError as e:
                    num_retries += 1
                    log(
                        "Error {status} while downloading {pn}, retrying attempt #{num_retries}/{MAX_RETRIES}".format(
                            status=e.response.status_code, pn=pn, num_retries=num_retries, MAX_RETRIES=MAX_RETRIES
                        )
                    )
            else:
                log("Failed to download {pn} after {num_retries} retries".format(pn=pn, num_retries=num_retries))
                continue

        # Now upload to artifactory, if we have credentials
        if art_helper:
            log("Uploading {pn} to artifactory".format(pn=pn))
            response = art_helper.upload_file(filepath=fn)
            response.raise_for_status()
    # for packages
# for buckets

log("All done")
