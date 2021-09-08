import logging
import requests.auth
import threading
from requests.cookies import extract_cookies_to_jar

## Redhat Token-based authentication
## Inspired by HTTPDigestAuth (see https://github.com/psf/requests/blob/main/requests/auth.py)

RHAPI_AUTH_URL = "https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token"


class RedHatTokenAuth(requests.auth.AuthBase):
    """Attaches Redhat token-based Authentication to the given Request object."""

    def __init__(self, offline_token):
        self.offline_token = offline_token
        # Keep state in per-thread local storage
        self._thread_local = threading.local()

    def init_per_thread_state(self):
        # Ensure state is initialized just once per-thread
        if not hasattr(self._thread_local, "init"):
            self._thread_local.init = True
            self._thread_local.access_token = None
            # Uncomment the following line to test the recovery path at the first attempt
            # self._thread_local.access_token = "WRONG_BY_DEFINITION"
            self._thread_local.num_401_calls = None

    def refresh_access_token(self):
        s = requests.Session()
        logging.info("Refreshing RedHat access token")
        url = RHAPI_AUTH_URL
        data = {
            "grant_type": "refresh_token",
            "client_id": "rhsm-api",
            "refresh_token": self.offline_token,
        }

        response = s.post(url=url, data=data)

        # Try to provide some meaningful information in the most common case (wrong token)
        if response.status_code == 400:
            msg = "400 Client Error: while trying to obtain access/online token, provided offline token is invalid or expired"
            logging.error(msg)
            raise requests.exceptions.HTTPError(msg, response=response)

        js = response.json()
        self._thread_local.access_token = js["access_token"]
        logging.info("RedHat access token successfully refreshed")

    def set_auth_header(self, r):
        r.headers["Authorization"] = "Bearer {}".format(self._thread_local.access_token)

    def handle_redirect(self, r, **kwargs):
        """Reset num_401_calls counter on redirects."""
        if r.is_redirect:
            self._thread_local.num_401_calls = 1

    def handle_401(self, r, **kwargs):
        """
        Takes the given response and retries with bearer auth, if needed.

        :rtype: requests.Response
        """

        # If response is not 4xx, do not auth
        # See https://github.com/psf/requests/issues/3772
        if not 400 <= r.status_code < 500:
            self._thread_local.num_401_calls = 1
            return r

        logging.info("Received '{} {}' from {}".format(r.status_code, r.reason, r.request.url))

        if self._thread_local.num_401_calls < 2:
            self._thread_local.num_401_calls += 1

            self.refresh_access_token()

            # Consume content and release the original connection
            # to allow our new request to reuse the same one.
            r.content
            r.close()
            prep = r.request.copy()
            extract_cookies_to_jar(prep._cookies, r.request, r.raw)
            prep.prepare_cookies(prep._cookies)

            self.set_auth_header(prep)
            _r = r.connection.send(prep, **kwargs)
            _r.history.append(r)
            _r.request = prep
            return _r

        self._thread_local.num_401_calls = 1
        return r

    def __call__(self, r):
        # Initialize per-thread state, if needed
        self.init_per_thread_state()
        # If we have no access token available, just obtain one
        if not self._thread_local.access_token:
            self.refresh_access_token()

        if self._thread_local.access_token:
            self.set_auth_header(r)

        r.register_hook("response", self.handle_401)
        r.register_hook("response", self.handle_redirect)
        self._thread_local.num_401_calls = 1
        return r

    def __eq__(self, other):
        return all([self.offline_token == getattr(other, "offline_token", None)])

    def __ne__(self, other):
        return not self == other
