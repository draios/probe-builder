import bz2
import zlib
import requests
import traceback
import shutil

from concurrent.futures import ThreadPoolExecutor
import os
import logging

from probe_builder.context import DownloadConfig

try:
    import lzma
except ImportError:
    from backports import lzma

try:
    from queue import Queue
except ImportError:
    from Queue import Queue


logger = logging.getLogger(__name__)


def download_file(url, output_file, download_config=None):
    def download_temp_file(url, temp_file, download_config):
        if download_config is None:
            download_config = DownloadConfig.default()
        resp = None
        for i in range(download_config.retries):
            logger.debug('Downloading {} to {}, attempt {} of {}'.format(url, temp_file, i+1, download_config.retries))
            with open(temp_file, 'ab') as fp:
                size = fp.tell()
                if size > 0:
                    headers = {'Range': 'bytes={}-'.format(size)}
                else:
                    headers = {}
                if download_config.extra_headers is not None:
                    headers.update(download_config.extra_headers)
                resp = requests.get(url, headers=headers, stream=True, timeout=download_config.timeout)
                if resp.status_code == 206:
                    # yay, resuming the download
                    shutil.copyfileobj(resp.raw, fp)
                    return
                elif resp.status_code == 416:
                    return  # "requested range not satisfiable", we have the whole thing
                elif resp.status_code == 200:
                    fp.truncate(0)  # have to start over
                    shutil.copyfileobj(resp.raw, fp)
                    return
        resp.raise_for_status()
        raise requests.HTTPError('Unexpected status code {}'.format(resp.status_code))

    # if target path already exists, assume it's complete
    if os.path.exists(output_file):
        logger.debug('Downloading {} to {} not necessary'.format(url, output_file))
        return
    # download to .part file
    temp_file = output_file + ".part"
    download_temp_file(url, temp_file, download_config)
    # and then rename it to its final target
    shutil.move(temp_file, output_file)

def download_batch(urls, output_dir, download_config=None):
    if download_config is None:
        download_config = DownloadConfig.default()

    # group all urls by target filename (basename), so to have a map:
    # {'file.ext': ['url1', 'url2']}
    urlmaps = {}
    for url in urls:
        urlmaps.setdefault(os.path.basename(url), []).append(url)

    # inner function to be used to download a single from multiple sources sequentially
    def download_multiple_sources(output_file, urls):
        for url in urls:
            try:
                download_file(url, output_file, download_config)
            except requests.exceptions.RequestException:
                traceback.print_exc()

    # use a parallel executor to download all stuff
    with ThreadPoolExecutor(max_workers=download_config.concurrency) as executor:
        download_futures = []
        for basename, urls in urlmaps.items():
            output_file = os.path.join(output_dir, basename)
            download_futures.append((basename, executor.submit(download_multiple_sources, output_file, urls)))

    for basename, future in download_futures:
        try:
            res = future.result()
        except:
            traceback.print_exc()
            print("^^^ While downloading {}".format(basename))


def get_url(url):
    resp = requests.get(url)
    resp.raise_for_status()
    if url.endswith('.gz'):
        return zlib.decompress(resp.content, 47)
    elif url.endswith('.xz'):
        return lzma.decompress(resp.content)
    elif url.endswith('.bz2'):
        return bz2.decompress(resp.content)
    else:
        return resp.content


def get_first_of(urls):
    last_exc = Exception('Empty url list')
    for url in urls:
        try:
            return get_url(url)
        except Exception as exc:
            last_exc = exc
    raise last_exc


if __name__ == '__main__':
    import sys

    _url = sys.argv[1]
    try:
        _output_file = sys.argv[2]
    except IndexError:
        _output_file = os.path.basename(_url)

    download_file(_url, _output_file)
