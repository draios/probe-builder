import logging
import requests.auth
from requests.cookies import extract_cookies_to_jar

## Red Hat Token-based authentication
## Inspired by HTTPDigestAuth (see https://github.com/psf/requests/blob/main/requests/auth.py)
## This class can be instantiated with a RedHat long-lived offline token.
## The resulting object, when passed as the auth argument to HTTP requests towards Red Hat API's, will:
## - transparently obtain a short-lived access token (through Red Hat's SSO)
## - automatically refresh such token when needed (i.e. after 15 minutes)
## - pass it to the actual HTTP request as "Authentication: Bearer" HTTP headers

RHAPI_AUTH_URL = "https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token"


class RedHatTokenAuth(requests.auth.AuthBase):
    """Attaches Red Hat token-based Authentication to the given Request object."""

    def __init__(self, offline_token):
        self.offline_token = offline_token

        self.access_token = None
        self.num_401_calls = None

        # If you want to test the automatic refresh/recovery path without having to wait 15 minutes,
        # Uncomment the following line and comment the one refreshing/pre-validating the access token
        #self.access_token = "WRONG_BY_DEFINITION"
        # Pre-validate offline token
        self.refresh_access_token()

    def refresh_access_token(self):
        s = requests.Session()
        logging.info("Refreshing Red Hat access token")
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
        self.access_token = js["access_token"]
        logging.info("Red Hat access token successfully refreshed")

    def set_auth_header(self, r):
        r.headers["Authorization"] = "Bearer {}".format(self.access_token)

    def handle_redirect(self, r, **kwargs):
        """Reset num_401_calls counter on redirects."""
        if r.is_redirect:
            self.num_401_calls = 1

    def handle_401(self, r, **kwargs):
        """
        Take the given response and if the status code is 4xx, refresh the access token and retry with bearer authentication

        :rtype: requests.Response
        """

        # If response is not 4xx, do not auth
        # See https://github.com/psf/requests/issues/3772
        if not 400 <= r.status_code < 500:
            self.num_401_calls = 1
            return r

        logging.info("Received '{} {}' from {}".format(r.status_code, r.reason, r.request.url))

        # The logic for num_401_calls is:
        # --> You get 401 once
        #    --> access token absent or expired
        #       --> get a new one and retry
        # --> You get 401 twice
        #    --> access token is invalid
        #      --> reset counter and give up
        #        --> have the original issuer deal with it
        #
        if self.num_401_calls < 2:
            self.num_401_calls += 1

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

        self.num_401_calls = 1
        return r

    def __call__(self, r):
        # If we have no access token available, just obtain one
        if not self.access_token:
            self.refresh_access_token()

        if self.access_token:
            self.set_auth_header(r)

        r.register_hook("response", self.handle_401)
        r.register_hook("response", self.handle_redirect)
        self.num_401_calls = 1
        return r

    def __eq__(self, other):
        return all([self.offline_token == getattr(other, "offline_token", None)])

    def __ne__(self, other):
        return not self == other
