import base64
import functools
import json as simplejson
import mimetypes
import os
import random
import re
import ssl

import six
from six.moves import http_cookiejar
from six.moves import urllib


__version__ = '0.7'
_user_agent = 'notrequests/' + __version__
LATIN1 = 'latin-1'
JSON_TYPE = 'application/json'
BINARY_TYPE = 'application/octet-stream'

_codes = {
    # Informational.
    100: 'continue',
    101: 'switching_protocols',
    102: 'processing',
    200: 'ok',
    201: 'created',
    202: 'accepted',
    203: 'non_authoritative_information',
    204: 'no_content',
    205: 'reset_content',
    206: 'partial_content',

    # Redirection.
    300: 'multiple_choices',
    301: 'moved_permanently',
    302: 'found',
    303: 'see_other',
    304: 'not_modified',
    305: 'use_proxy',
    306: 'switch_proxy',
    307: 'temporary_redirect',

    # Client error.
    400: 'bad_request',
    401: 'unauthorized',
    402: 'payment_required',
    403: 'forbidden',
    404: 'not_found',
    405: 'method_not_allowed',
    406: 'not_acceptable',
    407: 'proxy_authentication_required',
    408: 'request_timeout',
    409: 'conflict',
    410: 'gone',
    411: 'length_required',
    412: 'precondition_failed',
    413: 'request_entity_too_large',
    414: 'request_uri_too_long',
    415: 'unsupported_media_type',
    416: 'requested_range_not_satisfiable',
    417: 'expectation_failed',

    # Server error.
    500: 'internal_server_error',
    501: 'not_implemented',
    502: 'bad_gateway',
    503: 'service_unavailable',
    504: 'gateway_timeout',
    505: 'http_version_not_supported',
}


class PropertyDict(dict):
    def __getattr__(self, name):
        return self.get(name)


codes = PropertyDict((_codes[k], k) for k in _codes)


# For compatibility with code expecting requests' error classes.
class RequestException(IOError):
    """Something went wrong when making the request."""


class HTTPError(RequestException):
    """An HTTP error occurred."""


class Request(urllib.request.Request):
    def __init__(self, method, url, **kwargs):
        self._method = method
        urllib.request.Request.__init__(self, url, **kwargs)

    def get_method(self):
        return self._method


class Response(object):
    def __init__(self, addinfourl, request):
        self._r = addinfourl
        self.request = request
        self.status_code = self._r.getcode()
        self.headers = self._r.headers
        self.cookies = self._read_cookies(self._r, request)
        self.url = self._r.geturl()
        self.content = self._r.read()

    @classmethod
    def _read_cookies(cls, response, request):
        jar = http_cookiejar.CookieJar()
        jar.extract_cookies(response, request)

        return {cookie.name: cookie.value for cookie in jar}

    @classmethod
    def _encoding_from_message(cls, message):
        if six.PY2:
            for value in message.getplist():
                if value[:8] == 'charset=':
                    return value[8:]
        else:
            return message.get_content_charset()

    def json(self, **kwargs):
        """Decodes response as JSON."""
        encoding = detect_encoding(self.content[:4])
        value = self.content.decode(encoding)

        return simplejson.loads(value, **kwargs)

    @property
    def text(self):
        encoding = self._encoding_from_message(self.headers)

        return self.content.decode(encoding)

    @property
    def links(self):
        """A dict of dicts parsed from the response 'Link' header (if set)."""
        # <https://example.com/?page=2>; rel="next", <https://example.com/?page=34>; rel="last"'
        # becomes
        # {
        #     'last': {'rel': 'last', 'url': 'https://example.com/?page=34'},
        #     'next': {'rel': 'next', 'url': 'https://example.com/?page=2'},
        # },
        result = {}
        if 'Link' in self.headers:
            value = self.headers['Link']

            for part in re.split(r', *<', value):
                link = {}
                vs = part.split(';')

                # First section is always an url.
                link['url'] = vs.pop(0).strip('\'" <>')

                for v in vs:
                    if '=' in v:
                        key, v = v.split('=')
                        link[key.strip('\'" ')] = v.strip('\'" ')

                rkey = link.get('rel') or link['url']
                result[rkey] = link

        return result

    @property
    def ok(self):
        try:
            self.raise_for_status()
        except HTTPError:
            return False
        else:
            return True

    def raise_for_status(self):
        """Raises HTTPError if the request got an error."""
        if 400 <= self.status_code < 600:
            message = 'Error %s for %s' % (self.status_code, self.url)
            raise HTTPError(message)


class HTTPErrorHandler(urllib.request.HTTPDefaultErrorHandler):
    def http_error_default(self, req, fp, code, msg, hdrs):
        # urllib2 raises an exception on 4xx and 5xx. Make us behave more like
        # requests.
        return fp


class HTTPRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # urllib2 follows redirects by default. This handler doesn't.
        return None


def detect_encoding(value):
    """Returns the character encoding for a JSON string."""
    # https://tools.ietf.org/html/rfc4627#section-3
    if six.PY2:
        null_pattern = tuple(bool(ord(char)) for char in value[:4])
    else:
        null_pattern = tuple(bool(char) for char in value[:4])

    encodings = {
        # Zero is a null-byte, 1 is anything else.
        (0, 0, 0, 1): 'utf-32-be',
        (0, 1, 0, 1): 'utf-16-be',
        (1, 0, 0, 0): 'utf-32-le',
        (1, 0, 1, 0): 'utf-16-le',
    }

    return encodings.get(null_pattern, 'utf-8')


def _build_opener(allow_redirects=True, verify=True):
    # We need a custom opener so we can choose to not follow redirects and
    # not treat 4xx and 5xx responses as errors.
    handlers = [HTTPErrorHandler]
    if not allow_redirects:
        handlers.append(HTTPRedirectHandler)

    if not verify:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        handler = urllib.request.HTTPSHandler(context=ssl_context)
        handlers.append(handler)

    opener = urllib.request.build_opener(*handlers)

    return opener


def _encode_basic_auth(name, password):
    value = ('%s:%s' % (name, password)).encode(LATIN1).strip()
    value = b'Basic ' + base64.b64encode(value)

    return value


def _encode_data(data):
    """Handle a mapping or a sequence of pairs."""
    return urllib.parse.urlencode(data, doseq=True)


def _guess_filename(fileobj):
    name = getattr(fileobj, 'name', None)
    if name and name[:1] != '<' and name[-1:] != '>':
        return os.path.basename(name)


def _choose_boundary():
    chars = 'abcdefghijklmnopqrstuvwxyz123456789'
    boundary = ''.join(random.choice(chars) for _ in range(40))

    return boundary.encode('ascii')


def _build_form_data(data=None, files=None):
    # https://pymotw.com/2/urllib2/#uploading-files
    boundary = _choose_boundary()
    parts = []
    parts_boundary = b'--' + boundary

    # Has to be a dict if you are uploading files.
    if data:
        for field_name in sorted(data):
            parts.extend([
                parts_boundary,
                ('Content-Disposition: form-data; name="%s"' % field_name).encode(LATIN1),
                b'',
                data[field_name],
            ])

    if files:
        # files is a dict or list of 2-tuples, but the values can be
        # - a file-like object open for reading
        # - a pair of (filename, file-like object)
        # - a pair of (filename, byte string)
        if isinstance(files, dict):
            files = sorted(files.items())

        for field_name, name_and_file in files:
            if hasattr(name_and_file, 'read'):
                name = _guess_filename(name_and_file) or field_name
                value = name_and_file
            else:
                name, value = name_and_file

            content_type = (mimetypes.guess_type(name)[0] or BINARY_TYPE).encode(LATIN1)

            if not isinstance(value, six.binary_type):
                value = value.read()

            parts.extend([
                parts_boundary,
                ('Content-Disposition: file; name="%s"; filename="%s"' % (field_name, name)).encode(LATIN1),
                b'Content-Type: ' + content_type,
                b'',
                value,
            ])

    parts.extend([
        parts_boundary + b'--',
        b'',
    ])

    content_type = b'multipart/form-data; boundary=' + boundary
    data = b'\r\n'.join(parts)

    return content_type, data


def build_cookie(name, value):
    return http_cookiejar.Cookie(
        version=0,
        name=name,
        value=value,
        port=None,
        port_specified=False,
        domain='',
        domain_specified=False,
        domain_initial_dot=False,
        path='/',
        path_specified=False,
        secure=False,
        expires=None,
        discard=True,
        comment=None,
        comment_url=None,
        rest={'HttpOnly': None},
        rfc2109=False,
    )


def _merge_params(url, params):
    """Merge and encode query parameters with an URL."""
    if isinstance(params, dict):
        params = list(params.items())

    scheme, netloc, path, query, fragment = urllib.parse.urlsplit(url)
    url_params = urllib.parse.parse_qsl(query, keep_blank_values=True)
    url_params.extend(params)

    query = _encode_data(url_params)

    return urllib.parse.urlunsplit((scheme, netloc, path, query, fragment))


def _build_request(method, url, params=None, data=None, headers=None,
            cookies=None, auth=None, json=None, files=None):
    headers = {k.lower(): v for k, v in headers.items()} if headers else {}
    headers.setdefault('user-agent', _user_agent)

    if params:
        url = _merge_params(url, params)

    if auth:
        name, password = auth
        headers['authorization'] = _encode_basic_auth(name, password)

    if data and not files and not isinstance(data, six.binary_type):
        data = _encode_data(data)
        data = data.encode('ascii')

    if json:
        # If you send data and json, json overwrites data.
        data = simplejson.dumps(json).encode('utf-8')
        headers['content-type'] = JSON_TYPE

    if files:
        content_type, data = _build_form_data(data, files)
        headers['content-type'] = content_type

    request = Request(method, url, data=data, headers=headers)

    if cookies:
        jar = http_cookiejar.CookieJar()
        for key, value in cookies.items():
            cookie = build_cookie(key, value)
            jar.set_cookie(cookie)

        jar.add_cookie_header(request)

    return request


def _build_response(urllib_response, request):
    response = Response(urllib_response, request)

    return response


def request(method, url, params=None, data=None, headers=None, cookies=None,
            auth=None, json=None, files=None, allow_redirects=True, verify=True,
            timeout=None):
    request = _build_request(
        method,
        url,
        params=params,
        data=data,
        headers=headers,
        cookies=cookies,
        auth=auth,
        json=json,
        files=files,
    )

    _opener = _build_opener(allow_redirects=allow_redirects, verify=verify)

    # Better than trying to re-use urllib2's default timeout value. For regular
    # Python a timeout raises socket.timeout but App Engine will raise
    # google.appengine.api.urlfetch_errors.DeadlineExceededError.
    kwargs = {} if timeout is None else {'timeout': timeout}
    urllib_response = _opener.open(request, **kwargs)

    return _build_response(urllib_response, request)


delete = functools.partial(request, 'DELETE')
get = functools.partial(request, 'GET')
head = functools.partial(request, 'HEAD')
patch = functools.partial(request, 'PATCH')
post = functools.partial(request, 'POST')
put = functools.partial(request, 'PUT')


def patch():
    """Monkey-patch sys.modules so that other modules get notrequests when they
    do `import requests`.

    This will raise an exception if requests has already been imported, and only
    patches a few modules, not all of requests actual modules.

    Use this early in your app before any module tries to import requests.

    >>> import notrequests
    >>> notrequests.patch()
    """
    import imp
    import sys

    if 'requests' in sys.modules:
        raise Exception('Requests already imported, giving up.')

    mod = imp.new_module('requests.exceptions')

    mod.RequestException = RequestException
    mod.HTTPError = HTTPError

    sys.modules['requests'] = sys.modules[__name__]
    sys.modules['requests.exceptions'] = mod
