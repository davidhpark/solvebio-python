# -*- coding: utf-8 -*-
import json
import solvebio

from .version import VERSION
from .credentials import get_credentials
from .errors import SolveError

import platform
import requests
import textwrap
import logging
from urlparse import urljoin
from requests.auth import AuthBase

logger = logging.getLogger('solvebio')


def _handle_api_error(response):
    if response.status_code in [400, 401, 403, 404]:
        raise SolveError(response=response)
    else:
        logger.info('API Error: %d' % response.status_code)
        raise SolveError(response=response)


def _handle_request_error(e):
    if isinstance(e, requests.exceptions.RequestException):
        msg = SolveError.default_message
        err = "%s: %s" % (type(e).__name__, str(e))
    else:
        msg = ("Unexpected error communicating with SolveBio. "
               "It looks like there's probably a configuration "
               "issue locally. If this problem persists, let us "
               "know at contact@solvebio.com.")
        err = "A %s was raised" % (type(e).__name__,)
        if str(e):
            err += " with error message %s" % (str(e),)
        else:
            err += " with no error message"
    msg = textwrap.fill(msg) + "\n\n(Network error: %s)" % (err,)
    raise SolveError(message=msg)


class SolveTokenAuth(AuthBase):
    """Custom auth handler for SolveBio API token authentication"""

    def __init__(self, token=None):
        self.token = token or self._get_api_key()

    def __call__(self, r):
        if self.token:
            r.headers['Authorization'] = 'Token %s' % self.token
        return r

    def __repr__(self):
        return u'<SolveTokenAuth %s>' % self.token

    def _get_api_key(self):
        """
        Helper function to get the current user's API key or None.
        """
        if solvebio.api_key:
            return solvebio.api_key

        try:
            return get_credentials()[1]
        except:
            pass

        return None


class SolveClient(object):
    """A requests-based HTTP client for SolveBio API resources"""

    def __init__(self, api_key=None, api_host=None):
        self._api_key = api_key
        self._api_host = api_host
        self._headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip,deflate',
            'User-Agent': 'SolveBio Python Client %s [Python %s/%s]' % (
                VERSION,
                platform.python_implementation(),
                platform.python_version()
            )
        }

    @staticmethod
    def debug_request(method, url, params, data, _auth, _headers, files):
        from requests import Request, Session
        s = Session()
        req = Request(method=method.upper(),
                      url=url,
                      params=params,
                      data=data,
                      auth=_auth,
                      headers=_headers,
                      files=files)
        prepped = s.prepare_request(req)
        print(prepped.body)
        print(prepped.headers)

    def get(self, url, params, **kwargs):
        """Issues an HTTP GET across the wire via the Python requests
        library. See *request()* for information on keyword args."""
        kwargs['params'] = params
        return self.request('GET', url, **kwargs)

    def post(self,  url, data, **kwargs):
        """Issues an HTTP POST across the wire via the Python requests
        library. See *request* for information on keyword args."""
        kwargs['data'] = data
        return self.request('POST', url, **kwargs)

    def request(self, method, url, **kwargs):
        """
        Issues an HTTP Request across the wire via the Python requests
        library.

        Parameters
        ----------

        method : str
           an HTTP method: GET, PUT, POST, DELETE, ...

        url : str
           the place to connect to. If the url doesn't start
           with a protocol (https:// or http://), we'll slap
                solvebio.api_host in the front.

        allow_redirects: bool, optional
           set *False* we won't follow any redirects

        auth_class: function, optional
           Function to call to get an Authorization key. if not given
           we'll use self.api_key.

        headers: dict, optional

          Custom headers can be provided here; generally though this
          will be set correctly by default dependent on the
          method type. If the content type is JSON, we'll
          JSON-encode params.

        param : dict, optional
           passed as *params* in the requests.request

        timeout : int, optional
          timeout value in seconds for the request

        raw: bool, optional
          unless *True* the response encoded to json

        files: file
          File content in the form of a file handle which is to be
          uploaded. Files are passed in POST requests

        Returns
        -------
        response object. If *raw* is not *True* and
        repsonse if valid the object will be JSON encoded. Otherwise
        it will be the request.reposne object.
        """

        opts = {
            'allow_redirects': True,
            'auth':  SolveTokenAuth(),
            'data': {},
            'files': None,
            'headers': dict(self._headers),
            'params': {},
            'timeout': 80,
            'verify': True
            }

        if 'raw' in kwargs:
            raw = kwargs['raw']
            opts.pop('raw')
        else:
            raw = False

        opts.update(kwargs)

        method = method.upper()

        if opts['files']:
            # Don't use application/json for file uploads or GET requests
            opts['headers'].pop('Content-Type', None)
        else:
            opts['data'] = json.dumps(opts['data'])


        # Expand URL with API host if none was given
        api_host = self._api_host or solvebio.api_host

        if not api_host:
            raise SolveError(message='No SolveBio API host is set')
        elif not url.startswith(api_host):
            url = urljoin(api_host, url)

        logger.debug('API %s Request: %s' % (method, url))
        # self.debug_request(method, url, opts['params'], opts['data'],
        #                   opts['auth'], opts['headers'],
        #                   opts['files'])


        # And just when you thought we forgot about running the actual
        # request...
        try:
            response = requests.request(method, url, **opts)

        except Exception as e:
            _handle_request_error(e)

        if not (200 <= response.status_code < 400):
            _handle_api_error(response)

        # 204 is used on deletion. There is no JSON here.
        if raw or response.status_code in [204, 301, 302]:
            return response

        return response.json()

client = SolveClient()
