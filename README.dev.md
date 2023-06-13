# Developer notes

## Data flow through the application

Based on the command line arguments, a distribution is chosen.
This amounts to:
* a `DistroBuilder` subclass, containing distro-specific code
* a distribution name, used mostly as a directory name to store downloaded kernels
* a builder distro name, used to select a set of Dockerfiles to choose from
* a crawler distro name, passed to the kernel crawler (which has its own set of supported distributions)

Wherever `DistroBuilder` is mentioned in this document, it means a *subclass*
of the `DistroBuilder` class.

### Building probes from local files

#### Batching packages

The input is a list of paths to local files. `DistroBuilder.batch_packages` is called
to group the packages into kernel versions, resulting in a dictionary of arrays:

```json
{
  "5.4.0-1": [
    "kernel-5.4.0-1.x86_64.rpm",
    "kernel-devel-5.4.0-1.x86_64.rpm"
  ],
  "5.5.0-10": [
    "kernel-5.5.0-10.x86_64.rpm",
    "kernel-devel-5.5.0-10.x86_64.rpm"
  ]
}
```

(the package names here are obviously fake).

**Note:** this process doesn't inspect the packages themselves and only
relies on file names (like the old probe builder did). This means it may
be less accurate or completely wrong in some situations.

#### Unpacking the packages

The dictionary created above is passed to `DistroBuilder.unpack_kernels`.
This method uses distro-specific (or rather packager-specific) code to unpack
all packages in the per-release directories.

It returns a map of release->directory, similar to:

```json
{
  "5.4.0-1": ".../build/debian/5.4.0-1",
  "5.5.0-10": ".../build/debian/5.5.0-10"
}
```

(the directories are named in a way that is compatible with the old builder
so the mapping isn't always trivial, e.g. for Ubuntu kernels whose versioning
is somewhat complicated).

#### Building the kernels

For each (release, directory) pair returned from `unpack_kernels`,
`DistroBuilder.build_kernels` is called. This method is common to all
builders but it has per-distro extension points:

  * `get_kernel_dir`: return the full path to the kernel headers
    (the directory passed in is the root of the filesystem where the packages are extracted to,
    and the actual kernel directory is a subdirectory like `<directory>/usr/src/linux-headers-5.4.0-1`)
  * `hash_config`: return the MD5 hash of the kernel's config file
    (the config file is stored in different places for different distributions
    and this method knows where)

The rest of the code is distro-agnostic.

### Building probes for all kernels in a distribution

The kernel crawler has its own set of supported distributions, mostly
overlapping with the `DistroBuilder`s but e.g. Amazon Linux, Fedora and Oracle
Linux are compatible enough that they can use the CentOS builder, even though
they need their own crawlers (even if only to specify the list of mirrors).

In the crawler, each distribution is a set of mirrors, each of which can contain one
or more repositories. A repository knows how to parse its metadata and return a map
of release->list of URLs:

```json
{
  "5.4.0-1": [
    "http://.../kernel-5.4.0-1.x86_64.rpm",
    "http://.../kernel-devel-5.4.0-1.x86_64.rpm"
  ],
  "5.5.0-10": [
    "http://.../kernel-5.5.0-10.x86_64.rpm",
    "http://.../kernel-devel-5.5.0-10.x86_64.rpm"
  ]
}
```

The result of the crawler is used in `DistroBuilder.crawl` to download all
packages and replace the URLs with file paths. This is identical to the result
of `DistroBuilder.batch_packages` (used with local files), except that
the crawler understands repository metadata (which we don't have with local files)
so should generally make a better job of getting the right packages together.

The steps to unpack and build the kernels are identical in both cases.

### Add a caching proxy to speed up test runs

In order to speed up download during development/debugging, you might want to install
a caching proxy so that subsequent runs will be much faster.
One possible way is to use [Apache Traffic Server](https://docs.trafficserver.apache.org/en/latest/index.html).
**NOTE**: this will only work for http downloads.

Here is one known-to-work configuration:

```shell
$ traffic_server --version
Traffic Server 8.1.1 Jul 15 2021 19:48:17 localhost
traffic_server: using root directory '/usr'
Apache Traffic Server - traffic_server - 8.1.1 - (build # 071519 on Jul 15 2021 at 19:48:17)
```

```shell
$ diff -Naur /etc/trafficserver/records.config records.config
--- /etc/trafficserver/records.config	2021-07-15 21:48:17.000000000 +0200
+++ records.config	2022-03-18 16:10:10.219544524 +0100
@@ -103,7 +103,11 @@
     # https://docs.trafficserver.apache.org/records.config#proxy-config-http-cache-when-to-revalidate
 CONFIG proxy.config.http.cache.when_to_revalidate INT 0
     # https://docs.trafficserver.apache.org/records.config#proxy-config-http-cache-required-headers
-CONFIG proxy.config.http.cache.required_headers INT 2
+CONFIG proxy.config.http.cache.required_headers INT 0
+##### manually added, not originally present
+CONFIG proxy.config.http.cache.ignore_client_no_cache INT 1
+CONFIG proxy.config.http.cache.ignore_server_no_cache INT 1
+CONFIG proxy.config.http_ui_enabled INT 1

 ##############################################################################
 # Heuristic cache expiration. Docs:
@@ -153,11 +157,11 @@
 #    https://docs.trafficserver.apache.org/records.config#url-remap-rules
 #    https://docs.trafficserver.apache.org/en/latest/admin-guide/files/remap.config.en.html
 ##############################################################################
-CONFIG proxy.config.url_remap.remap_required INT 1
+CONFIG proxy.config.url_remap.remap_required INT 0
     # https://docs.trafficserver.apache.org/records.config#proxy-config-url-remap-pristine-host-hdr
 CONFIG proxy.config.url_remap.pristine_host_hdr INT 0
     # https://docs.trafficserver.apache.org/records.config#reverse-proxy
-CONFIG proxy.config.reverse_proxy.enabled INT 1
+CONFIG proxy.config.reverse_proxy.enabled INT 0

 ##############################################################################
 # SSL Termination. Docs:
```

```shell
$ diff -Naur /etc/trafficserver/storage.config storage.config
--- /etc/trafficserver/storage.config	2021-07-15 21:48:17.000000000 +0200
+++ storage.config	2022-03-18 15:49:53.017949468 +0100
@@ -50,4 +50,4 @@
 # A small default cache (256MB). This is set to allow for the regression test to succeed
 # most likely you'll want to use a larger cache. And, we definitely recommend the use
 # of raw devices for production caches.
-/var/cache/trafficserver 256M
+/var/cache/trafficserver 10280M
```

More information can be found in the [documentation](https://docs.trafficserver.apache.org/en/latest/admin-guide/configuration/cache-basics.en.html#caching-http-objects)

When running the  `sysdig-probe-builder` container, you only need to specify:

```shell
$ docker run -i --rm \
     <other args> \
     -e HTTP_PROXY=http://172.17.0.1:8080 \
     sysdig-probe-builder <entrypoint-args> -- <builder-args>
```

To check that it's actually working, you can
```
$ tail -f /var/log/trafficserver/extended2.log
172.17.0.2 - - [18/Mar/2022:16:58:20 +0100] "GET http://security.ubuntu.com/ubuntu/dists/focal-security/main/binary-amd64//Packages.xz HTTP/1.1" 200 1317228 000 0 0 0 234 362 0 0 0 NONE FIN FIN TCP_HIT
```

You want to make sure you have `TCP_HIT`
