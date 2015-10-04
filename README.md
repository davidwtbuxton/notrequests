Notrequests
===========

A Python wrapper for the built-in urllib2 module. The API is compatible with [the excellent Requests library][requests], but omitting features such as sessions and support for keep-alive.

Notrequests is intended for doing HTTP requests on [Google App Engine][gae] where Requests has some disadvantages.

It is not Python 3 compatible (yet).


Installation
------------

From PyPI:

    $ pip install notrequests

Or download and run setup as normal:

    $ curl -L -o notrequests.zip https://github.com/davidwtbuxton/notrequests/archive/master.zip
    $ unzip notrequests.zip
    $ cd notrequests-master
    $ python setup.py install


Usage
-----

Notrequests is compatible with the Requests API (or it tries to be).

    >>> import notrequests
    >>>
    >>> response = notrequests.get('http://httpbin.org/get')
    >>> response.status_code == notrequests.codes.ok
    True

But it doesn't do everything that Requests does. There's no session support, no keep-alive support and it reads the entire response into memory.

Notrequests uses urllib2 but behaves more like Requests. So it won't throw an exception on 4xx and 5xx responses.

    >>> response = notrequests.get('http://httpbin.org/status/404')
    >>> response.status_code == notrequests.codes.not_found
    True

You can do basic auth just like Requests (but not other authentication types):

    >>> url = 'http://httpbin.org/basic-auth/alice/secret'
    >>> response = notrequests.get(url)
    >>> response.status_code
    401
    >>> response = notrequests.get(url, auth=('alice', 'secret'))
    >>> response.status_code
    200

And send and decode JSON:

    >>> import pprint
    >>> response = notrequests.put('http://httpbin.org/put', json={'foo': ['bar', 'baz']})
    >>> data = response.json()
    >>> pprint.pprint(data)
    {u'args': {},
     u'data': u'{"foo": ["bar", "baz"]}',
     u'files': {},
     u'form': {},
     u'headers': {u'Accept-Encoding': u'identity',
                  u'Content-Length': u'23',
                  u'Content-Type': u'application/json',
                  u'Host': u'httpbin.org',
                  u'User-Agent': u'notrequests/0.1'},
     u'json': {u'foo': [u'bar', u'baz']},
     u'origin': u'10.10.10.1',
     u'url': u'http://httpbin.org/put'}

There's also support for uploading files:

    >>> import io
    >>> fileobj = io.BytesIO('foo bar baz')
    >>> response = notrequests.post('http://httpbin.org/post', files={'upload': fileobj})
    >>> response.json()['files']
    {u'upload': 'foo bar baz'}

As with Requests, the keys in the files dict are the form field input names and
the values in the files dict can be a 2-tuple of file name with file object or
byte string:

    >>> files = {'upload': ('my-file.txt', b'Foo\nbar\nbaz.')}
    >>> response = notrequests.post('http://httpbin.org/post', files=files)
    >>> print response.request.data
    --10.10.10.1.503.2717.1443987498.810.2
    Content-Disposition: file; name="upload"; filename="my-file.txt"
    Content-Type: text/plain

    Foo
    bar
    baz.
    --10.10.10.1.503.2717.1443987498.810.2--


API compatibility
-----------------

These are some features of [the Requests API][api] that Notrequests hasn't implemented. It isn't a complete list, and it would be nice to have better support.

- Sessions
- Request.text and auto-detection of encodings
- Response.history
- Response.raise_for_status()
- Response.links
- Streaming uploads / downloads and iterating over data
- Alternate names for status codes
- Proxies


Tests
-----

Run the tests with [tox][tox].

By default the tests make requests to http://httpbin.org, but you can run a local instance which will speed things up.

    $ pip install httpbin gunicorn
    $ gunicorn --bind 127.0.0.1:8888 httpbin:app
    $ export NOTREQUESTS_TEST_URL="http://127.0.0.1:8888"
    $ tox


Why not use Requests?
---------------------

Google App Engine patches httplib in the standard library to use its urlfetch service, and restricts [the sockets API][sockets] to paid applications. Requests does not use httplib and uses sockets.

If you want to use [the app identity service to authenticate connections between App Engine applications][appidentity] you have to use the urlfetch service, you cannot use Requests. Notrequests works because it uses urllib2, which uses httplib.


[requests]: http://www.python-requests.org/
[gae]: https://cloud.google.com/appengine/
[tox]: http://codespeak.net/tox/
[appidentity]: https://cloud.google.com/appengine/docs/python/appidentity/#Python_Asserting_identity_to_other_App_Engine_apps
[sockets]: https://cloud.google.com/appengine/docs/python/sockets/
[api]: http://requests.readthedocs.org/en/latest/api/
