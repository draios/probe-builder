Sysdig kmod build for OS4.x
===========================

# Introduction

This set of scripts is designed to exercise the Red Hat subscriber API to locate and download all the available kernel headers for RHEL-based OpenShift platforms. These scripts also contain tooling to upload those headers to Sysdig's internal artifact repository.

# Setup and prerequisites

## Python environment

These scripts are written in Python, so a reasonably recent python interpeter is a must. They also use `requests` to interact with various REST APIs. Depending on how your system distributes python packages, you
will either need to install the `requests` package from your package manager or install it using python's own package manager, `pip3`:

```
pip3 install requests
```

## API keys

### Red Hat API key

Your Red Hat subscriber account will need access to the Red Hat software respository located here:
https://access.redhat.com/downloads/content/package-browser. You will also need to have generated an API key for your account. The Red Hat subscriber API uses a two-phase key system: one key (called the **offline token**) which
you store permanently on your computer, and one key called an **access token** which gives access to the API for a short amount of time and then expires (15 minutes as of today). You need an offline token to be passed over to the script as a command line argument.
Please be aware that the **offline token** will **expire in 90 days** if left unused so you should run the script every once in a while to keep it alive.

### Artifactory API key
If you wish to upload to artifactory, you will also need an API key for artifactory.
You can generate one by logging in to artifactory as yourself, clicking on your email/username on the top right corner, and then clicking on "Edit Profile".
Notice how the generated API key could be used either for HTTP Basic Authentication (paired with your email), or by itself as a custom HTTP header. The script uses the `X-JFrog-Art-Api` custom header so your email will not be needed.

# Usage

The only required parameter is the RedHat API offline token, which should normally come in as a Jenkins secret. Other than that, sensible defaults have (hopefully) been provided. Most likely you will want to specify an output directory (default: current directory) using the `-o` flag.

## Parameters

| Parameter | Meaning | Default value | Examples |
| --- | --- | --- | --- |
| `-t` | Red Hat API token **(mandatory)** |  | `-t 6DhjYIFYM587anxFXg1XA6jTpNwWwoMuB2gBnlLR0SYYeGj4cpV1OAPmKaUfEDoh8XHIHWJvZ2D57bHdh5i7JOF7qedtphGNLXzGtRDTwyJqTYj5MScmqRy3VapnsgD2yhCBoJ1l4pJdvZuqblEZksOERPNGs5MKeBAMRazxLmlJF4ySv3tVhAp538KJLYtA7Z3We2fF6KKazdfLoaXy2uz0ViHiVidf7HHBwhsnlrBRjIqX4XJVrqeAEGnJvRb5dAjvOQDHxR0m7D3EQBA6AQEHu8ZCYPyRUL2JbBMi7DaSXZ3OdfSnfTiFprwF4TMnwbMEK9fuO3lMAaoBHA4WSmeSPFhSLtQdcqLdKfgj9cFEBR88H5unfqu5vOTNkBnZ3rqVyQpUBPyMprGERjkStTDq9bKFhh1GteNkb3InRVkb43hVNC3XCvX2Xyzff7iPIFRR41j2ClifGdBuqXdBXghBioT032mu6rVCCFtbkAV9Kbi98jh05l9mTLGs7pTmiMcMDtRSmIiqbRD2T7ZqWZrlTenVpyOa1fW9E3O4bD8Y8r6q6QaPm8AVDrVAujHKMmCN1CNVqHIaRO74vz2aYkC4R6eZtlDmzygxH5U1G2Ca0nI3s2Q67SpEhBAw` |
| `-o`, `--outdir` | Output directory (must exist) | `.` | `-o /tmp`, `-o headers` |
| `-b`, `--redhat-bucket` | RedHat bucket(s) to walk (may be used multiple times) | `rhel-8-for-x86_64-baseos-rpms`, `rhel-8-for-x86_64-baseos-eus-rpms`, `hocp-4.7-for-rhel-8-x86_64-rpms` | `-b hocp-4.7-for-rhel-8-x86_64-rpms` |
| `-a` | Artifactory base url | (None) | `-a https://artifactory.mycompany.com/artifactory` |
| `-A` | Artifactory API key | (None) | `-A  cmalzOJ7Vww8dKZv2Z7U9gifhjlrwQx6b44RPolzte00PEr9yVfjaGhclxGXXVFVre81S05Zs` |
| -i | Interactive mode - output progress reports to `stderr` |  |  |
| `-q` | Quiet mode - no output except critical errors | off | `-q` |
| `-v` | Verbose | off | `-v` |

## At runtime

The script takes a while to run -- about a minute and a half on my machine, more if it has to download and upload all the files. It will print helpful status updates so you know it hasn't fallen over (or, if it does, what happened).
Unless both `-A` and `-a` parameters are specified, the script will just skip over the parts where it tries to contact the artifactory server.

Please notice the following changes, compared to the previous implementation:

* SHA-256 is obtained from artifactory and compared with the one obtained from RedHat so that files already present in Artifactory bucket will be skipped only if they're identical to the ones present in RedHat's buckets
* The script transparently refreshes the RedHat access token as soon as the server starts complaining about it (i.e. normally after 15 minutes), so it is no longer necessary to expedite execution so to complete downloading before the token expires. So downloading from RedHat's servers is currently serialized for simplicity; nevertheless, it should be possible to run multiple downloads in parallel (4 looks like the optimal number before their servers start 429'ing) with some minor changes only.
