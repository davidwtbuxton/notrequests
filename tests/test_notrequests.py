#!/usr/bin/env python
import io
import json
import os
import socket
import ssl
import tempfile
import unittest
import warnings

import six
from six.moves import urllib

import notrequests as nr


def _url(path):
    # See README on how to use a local httpbin instance for testing.
    base_url = os.environ.get('NOTREQUESTS_TEST_URL', 'http://httpbin.org/')
    return urllib.parse.urljoin(base_url, path)


class PackageAPITestCase(unittest.TestCase):
    def test_api(self):
        nr.get
        nr.patch
        nr.post
        nr.put
        nr.delete
        nr.head
        nr.codes
        nr.HTTPError
        nr.RequestException


class GetTestCase(unittest.TestCase):
    def test_get(self):
        url = _url('/')
        response = nr.get(url)

        self.assertEqual(response.status_code, 200)

    def test_auth_get_allowed(self):
        url = _url('/basic-auth/foo/bar')
        response = nr.get(url, auth=('foo', 'bar'))

        self.assertEqual(response.status_code, 200)

    def test_auth_get_denied(self):
        url = _url('/basic-auth/foo/bar')
        response = nr.get(url, auth=('baz', 'qux'))

        self.assertEqual(response.status_code, 401)

    def test_setting_headers_on_get(self):
        url = _url('/headers')
        headers = {'X-Foo': 'bar'}
        response = nr.get(url, headers=headers)

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertIn('headers', data)
        self.assertIn('X-Foo', data['headers'])

    def test_headers_case_normalized(self):
        url = _url('/headers')
        headers = {'X-FOO-bar-Baz': 'BAR'}
        response = nr.get(url, headers=headers)

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertIn('headers', data)
        self.assertIn('X-Foo-Bar-Baz', data['headers'])

    def test_get_500_response(self):
        url = _url('/status/500')
        response = nr.get(url)

        self.assertEqual(response.status_code, 500)

    def test_sending_cookies(self):
        url = _url('/cookies')
        cookies = {'foo': 'bar'}
        response = nr.get(url, cookies=cookies)

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data, {'cookies': {'foo': 'bar'}})

    def test_receiving_cookies(self):
        url = _url('/cookies/set?foo=bar')
        response = nr.get(url, allow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.cookies, {'foo': 'bar'})

    def test_params_dict_sets_query_string(self):
        url = _url('/get')
        params = {'foo': 'bar'}
        response = nr.get(url, params=params)

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data['args'], params)

    def test_params_merged_with_url_query_string(self):
        url = _url('/get?foo=bar')
        params = {'foo': 'baz'}
        response = nr.get(url, params=params)

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data['args'], {'foo': ['bar', 'baz']})

    def test_params_tuple_sets_query_string(self):
        url = _url('/get')
        params = (('foo', 'bar'), ('baz', 'qux'),)
        response = nr.get(url, params=params)

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data['args'], {'foo': 'bar', 'baz': 'qux'})

    def test_verify_ssl_is_true(self):
        url = 'https://swupdl.adobe.com'

        with self.assertRaises(ssl.CertificateError):
            response = nr.get(url, verify=True)

    def test_verify_ssl_is_false(self):
        url = 'https://swupdl.adobe.com'
        response = nr.get(url, verify=False)

        # The important thing is it didn't throw an exception.
        self.assertEqual(response.status_code, 404)

    def test_timeout_keyword(self):
        url = _url('/')
        response = nr.get(url, timeout=60)

    def test_timeout_raises_error(self):
        # On App Engine I think it raises DeadlineExceededError.
        url = _url('/delay/2')

        with self.assertRaises(socket.timeout):
            response = nr.get(url, timeout=1)

    def test_timeout_does_not_raise_error(self):
        url = _url('/delay/1')
        response = nr.get(url, timeout=2)

        self.assertEqual(response.status_code, 200)


class PatchTestCase(unittest.TestCase):
    def test_patch(self):
        url = _url('/patch')
        response = nr.patch(url)

        self.assertEqual(response.status_code, 200)


class PostTestCase(unittest.TestCase):
    def test_sending_data_dict_is_form_encoded(self):
        url = _url('/post')
        request_data = {
            'foo': 'bar baz',
        }
        response = nr.post(url, data=request_data)

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data['headers']['Content-Type'], 'application/x-www-form-urlencoded')
        self.assertEqual(data['form'], request_data)

    def test_sending_data_as_bytes(self):
        url = _url('/post')
        request_data = json.dumps({'foo': 'bar'}).encode('utf-8')
        headers={'Content-Type': 'application/json'}
        response = nr.post(url, data=request_data, headers=headers)

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data['headers']['Content-Type'], 'application/json')
        self.assertEqual(data['data'], '{"foo": "bar"}')

    def test_json_keyword(self):
        url = _url('/post')
        json_data = {'foo': 'bar'}
        response = nr.post(url, json=json_data)

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data['data'], '{"foo": "bar"}')
        self.assertEqual(data['headers']['Content-Type'], 'application/json')

    def test_submit_file_with_file_object(self):
        url = _url('/post')
        files = {'file': io.BytesIO(b'binarydata')}
        response = nr.post(url, files=files)

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data['files'], {'file': 'binarydata'})

    def test_submit_file_with_name_and_file_object(self):
        url = _url('/post')
        files = {'file': ('foo.txt', io.BytesIO(b'binarydata'))}
        response = nr.post(url, files=files)

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data['files'], {'file': 'binarydata'})

    def test_submit_file_with_name_and_byte_string(self):
        url = _url('/post')
        files = {'file': ('foo.txt', b'binarydata')}
        response = nr.post(url, files=files)

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data['files'], {'file': 'binarydata'})

    def test_submit_file_with_file_from_disk(self):
        # This exercises the code which guesses the uploaded filename from
        # the open file handle.

        url = _url('/post')
        _, path = tempfile.mkstemp()

        with open(path, 'wb') as fh:
            fh.write(b'binarydata')

        try:
            with open(path, 'rb') as fh:
                files = {'file': fh}
                response = nr.post(url, files=files)

            self.assertEqual(response.status_code, 200)

            data = response.json()

            self.assertEqual(data['files'], {'file': 'binarydata'})
        finally:
            os.unlink(path)

    def test_submit_file_and_form_data(self):
        url = _url('/post')
        files = {'file': io.BytesIO(b'binarydata')}
        request_data = {'foo': b'bar baz'}
        response = nr.post(url, files=files, data=request_data)

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data['files'], {'file': 'binarydata'})
        self.assertEqual(data['form'], {'foo': 'bar baz'})


class PutTestCase(unittest.TestCase):
    def test_put(self):
        url = _url('/put')
        response = nr.put(url)

        self.assertEqual(response.status_code, 200)


class DeleteTestCase(unittest.TestCase):
    def test_delete(self):
        url = _url('/delete')
        response = nr.delete(url)

        self.assertEqual(response.status_code, 200)


class HeadTestCase(unittest.TestCase):
    def test_head(self):
        url = _url('/get')
        response = nr.head(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'')


class ResponseTestCase(unittest.TestCase):
    def test_decode_json(self):
        url = _url('/user-agent')
        response = nr.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'user-agent': nr._user_agent})

    def test_status_code(self):
        url = _url('/user-agent')
        response = nr.get(url)

        self.assertEqual(response.status_code, 200)

    def test_content(self):
        url = _url('/user-agent')
        response = nr.get(url)
        expected = ('{\n  "user-agent": "%s"\n}\n' % nr._user_agent).encode('latin-1')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, expected)

    def test_decoding_text_with_encoding_header(self):
        url = _url('/encoding/utf8')
        response = nr.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-Type'], 'text/html; charset=utf-8')
        self.assertIsInstance(response.text, six.text_type)
        self.assertEqual(response.text[:21], u'<h1>Unicode Demo</h1>')

    def test_links_property_with_valid_link_header(self):
        url = _url('/response-headers')
        link = '<https://example.com/?page=2>; rel="next", <https://example.com/?page=34>; rel="last"'
        response = nr.get(url, params={'Link': link})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Link'], link)
        self.assertEqual(
            response.links,
            {
                'last': {'rel': 'last', 'url': 'https://example.com/?page=34'},
                'next': {'rel': 'next', 'url': 'https://example.com/?page=2'},
            },
        )

    def test_links_property_with_no_link_header(self):
        url = _url('/response-headers')
        response = nr.get(url, params={})

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Link', response.headers)
        self.assertEqual(response.links, {})

    def test_cookies_are_decoded_correctly(self):
        # Previously we caused cookielib errors trying to parse complex cookies.
        # http://www.adobe.com/support/downloads/product.jsp?product=1&platform=Windows

        url = _url('/response-headers')
        # Domain can changed depending on NOTREQUESTS_TEST_URL being set.
        domain = urllib.parse.urlparse(url).netloc.split(':')[0]

        # httpbin's /cookies/set path doesn't allow us to specify domain, so
        # set the full cookie header value manually.
        cookie_values = [
            'JSESSIONID=ABC123; Path=/',
            'dtCookie=DEF456; Path=/; Domain={}',
            'AWID=GHI789; Version=1; Comment="hello"; Domain={}; Max-Age=315360000; Path=/',
        ]

        with warnings.catch_warnings(record=True) as raised_warnings:
            warnings.simplefilter('always')

            params = [('Set-Cookie', value.format(domain)) for value in cookie_values]
            response = nr.get(url, params=params, allow_redirects=False)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(raised_warnings, [])
        self.assertEqual(
            response.cookies,
            {
                'JSESSIONID': 'ABC123',
                'dtCookie': 'DEF456',
                'AWID': 'GHI789',
            },
        )

    def test_raise_for_status_raises_error_for_404(self):
        url = _url('/status/404')
        response = nr.get(url)

        with self.assertRaisesRegexp(nr.HTTPError, r'Error 404 for %s' % url):
            response.raise_for_status()

    def test_raise_for_status_raises_error_for_500(self):
        url = _url('/status/500')
        response = nr.get(url)

        with self.assertRaisesRegexp(nr.HTTPError, r'Error 500 for %s' % url):
            response.raise_for_status()

    def test_raise_for_status_no_error(self):
        url = _url('/status/200')
        response = nr.get(url)

        self.assertIsNone(response.raise_for_status())

    def test_response_ok_true(self):
        url = _url('/status/200')
        response = nr.get(url)

        self.assertTrue(response.ok)

    def test_response_ok_false(self):
        url = _url('/status/404')
        response = nr.get(url)

        self.assertFalse(response.ok)


class CodesTestCase(unittest.TestCase):
    def test_access_status_codes_as_properties(self):
        self.assertEqual(nr.codes.ok, 200)


class DetectEncodingTestCase(unittest.TestCase):
    def test_detect_utf8(self):
        value = json.dumps({'foo': 'bar'}).encode('utf-8')
        result = nr.detect_encoding(value)

        self.assertEqual(result, 'utf-8')

    def test_detect_utf16le(self):
        value = json.dumps({'foo': 'bar'}).encode('utf-16-le')
        result = nr.detect_encoding(value)

        self.assertEqual(result, 'utf-16-le')

    def test_detect_utf16be(self):
        value = json.dumps({'foo': 'bar'}).encode('utf-16-be')
        result = nr.detect_encoding(value)

        self.assertEqual(result, 'utf-16-be')

    def test_detect_utf32le(self):
        value = json.dumps({'foo': 'bar'}).encode('utf-32-le')
        result = nr.detect_encoding(value)

        self.assertEqual(result, 'utf-32-le')

    def test_detect_utf32be(self):
        value = json.dumps({'foo': 'bar'}).encode('utf-32-be')
        result = nr.detect_encoding(value)

        self.assertEqual(result, 'utf-32-be')


if __name__ == '__main__':
    unittest.main()
