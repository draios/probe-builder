import json
import os

from .spawn import pipe, json_pipe


class DockerVolume(object):
    host_path = None
    container_path = None
    readonly = True

    def __init__(self, host_path, container_path, readonly=True):
        self.host_path = host_path
        self.container_path = container_path
        self.readonly = readonly

    def __str__(self):
        if self.readonly:
            return '{}:{}:ro'.format(self.host_path, self.container_path)
        else:
            return '{}:{}'.format(self.host_path, self.container_path)


class EnvVar(object):
    name = None
    value = None

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __str__(self):
        return '{}={}'.format(self.name, self.value)


def run(image, volumes, command, env, privileged=False, name=None, arch=None):
    cmd = ['docker', 'run', '--rm']
    if privileged:
        cmd.append('--privileged')
    for volume in volumes:
        cmd.append('-v')
        cmd.append(str(volume))
    for var in env:
        cmd.append('-e')
        cmd.append(str(var))
    if name is not None:
        cmd.append('--name')
        cmd.append(str(name))
    if arch is not None:
        image = '{}-{}'.format(image, arch)
    cmd.append(image)
    cmd.extend(command)

    # return stdout
    return pipe(cmd)


def build(arch, image, dockerfile, context_dir):
    p = [
        'docker',
        'buildx',
        'build',
        '-t', '{}-{}'.format(str(image), arch) if arch else '{}'.format(str(image)),
        '-f', str(dockerfile)
    ]
    if arch:
        p += ['--platform=linux/{}'.format(arch)]

    p += [str(context_dir)]

    pipe(p)
    remove_dangling_images()


def rm(container_name):
    pipe(['docker', 'rm', container_name], silence_errors=True)


def inspect_self():
    try:
        hostname = os.uname()[1]
        return json_pipe(['docker', 'inspect', hostname], silence_errors=True)
    except Exception:
        pass


def get_mount_mapping():
    inspect = inspect_self()
    if inspect is None:
        return
    mounts = []
    for mount in inspect[0]['Mounts']:
        mounts.append((mount['Destination'], mount['Source']))
    return mounts


def is_privileged():
    inspect = inspect_self()
    if inspect is None:
        return True
    try:
        if inspect[0]['HostConfig']['Privileged'] == 'true':
            return True
    except:
        return False


def remove_dangling_images():
    images = pipe(['docker', 'images', '-q', '-f', 'dangling=true'])
    if images:
        pipe(['docker', 'rmi'] + images.splitlines(False), silence_errors=True)
