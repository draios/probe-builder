import requests
import os


class ArtifactoryHelper:
    def __init__(self, base_url, bucket, apikey):
        self.base_url = base_url
        self.bucket = bucket
        self.apikey = apikey

    def list_artifacts(self):
        s = requests.Session()

        url = "{base_url}/api/storage/{bucket}".format(base_url=self.base_url, bucket=self.bucket)
        headers = {
            "accept": "application/json",
            "X-JFrog-Art-Api": self.apikey,
        }
        # see https://www.jfrog.com/confluence/display/RTF6X/Artifactory+REST+API#ArtifactoryRESTAPI-FileList
        params = "list"

        response = s.get(url=url, headers=headers, params=params)
        response.raise_for_status()
        # expected output looks like:
        # {
        #   'uri': '{base_url}/api/storage/{bucket}',
        #   'created': '2021-09-07T09:32:39.948Z',
        #   'files': [
        #       {'uri': '/README', 'size': 252, 'lastModified': '2019-07-15T21:54:43.716Z', 'folder': False, 'sha1': 'e23c510e0281969da2ed4a76910103861f91051e', 'sha2': 'bc3db5a0bf0a0e5a452df216a179e15665b93591d1dab850770acfebbf75b9ba'},
        #       ...
        #    ]
        # }
        j = response.json()
        # print(j)
        return {file["uri"].lstrip("/"): file["sha2"] for file in j["files"] if not file["folder"]}

    def upload_file(self, filepath):
        s = requests.Session()
        fn = os.path.basename(filepath)

        url = "{base_url}/{bucket}/{fn}".format(base_url=self.base_url, bucket=self.bucket, fn=fn)
        headers = {
            "Content-Type": "application/octet-stream",
            "X-JFrog-Art-Api": self.apikey,
        }
        response = None
        with open(filepath, "rb") as f:
            data = f.read()  # read entire file as bytes
            response = s.put(url=url, headers=headers, data=data)

        return response
