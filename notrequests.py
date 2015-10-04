import base64
import cookielib
import functools
import json as simplejson
import urllib
import urllib2


__version__ = '0.1'
_user_agent = 'notrequests/' + __version__
LATIN1 = 'latin-1'
JSON_TYPE = 'application/json'

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


class Request(urllib2.Request):
    def __init__(self, method, url, **kwargs):
        self._method = method
        urllib2.Request.__init__(self, url, **kwargs)

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
        jar = cookielib.CookieJar()
        cookies = jar.make_cookies(response, request)

        return {c.name: c.value for c in cookies}

    def json(self):
        """Decodes response as JSON."""
        return simplejson.loads(self.content)


class HTTPErrorHandler(urllib2.HTTPDefaultErrorHandler):
    def http_error_default(self, req, fp, code, msg, hdrs):
        # urllib2 raises an exception on 4xx and 5xx. Make us behave more like
        # requests.
        return fp


class HTTPRedirectHandler(urllib2.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # urllib2 follows redirects by default. This handler doesn't.
        return None


def _build_opener(allow_redirects=True):
    # We need a custom opener so we can choose to not follow redirects and
    # not treat 4xx and 5xx responses as errors.
    handlers = [HTTPErrorHandler]
    if not allow_redirects:
        handlers.append(HTTPRedirectHandler)

    opener = urllib2.build_opener(*handlers)

    return opener


def _encode_basic_auth(name, password):
    value = ('%s:%s' % (name, password)).encode(LATIN1).strip()
    value = 'Basic ' + base64.b64encode(value)

    return value


def _encode_data(data):
    """Handle a mapping or a sequence of pairs."""
    return urllib.urlencode(data, doseq=True)


def build_cookie(name, value):
    return cookielib.Cookie(
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


def _build_request(method, url, params=None, data=None, headers=None,
            cookies=None, auth=None, json=None):
    headers = {k.lower(): v for k, v in headers.items()} if headers else {}
    headers.setdefault('user-agent', _user_agent)

    if auth:
        name, password = auth
        headers['authorization'] = _encode_basic_auth(name, password)

    if data and not isinstance(data, str):
        data = _encode_data(data)

    if json:
        # If you send data and json, json overwrites data.
        data = simplejson.dumps(json)
        headers['content-type'] = JSON_TYPE

    request = Request(method, url, data=data, headers=headers)

    if cookies:
        jar = cookielib.CookieJar()
        for key, value in cookies.items():
            cookie = build_cookie(key, value)
            jar.set_cookie(cookie)

        jar.add_cookie_header(request)

    return request


def _build_response(urllib_response, request):
    response = Response(urllib_response, request)

    return response


def request(method, url, params=None, data=None, headers=None, cookies=None,
            auth=None, json=None, allow_redirects=True):
    request = _build_request(
        method,
        url,
        data=data,
        headers=headers,
        cookies=cookies,
        auth=auth,
        json=json,
    )

    _opener = _build_opener(allow_redirects=allow_redirects)

    urllib_response = _opener.open(request)
    return _build_response(urllib_response, request)


get = functools.partial(request, 'GET')
patch = functools.partial(request, 'PATCH')
post = functools.partial(request, 'POST')
put = functools.partial(request, 'PUT')
delete = functools.partial(request, 'DELETE')
head = functools.partial(request, 'HEAD')
