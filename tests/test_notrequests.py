import json
import os
import unittest
import urllib2
import urlparse

import notrequests as nr


def _url(path):
    # See README on how to use a local httpbin instance for testing.
    base_url = os.environ.get('NOTREQUESTS_TEST_URL', 'http://httpbin.org/')
    return urlparse.urljoin(base_url, path)


class PackageAPITestCase(unittest.TestCase):
    def test_api(self):
        nr.get
        nr.post
        nr.put
        nr.delete
        nr.codes


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

        data = json.loads(response.content)

        self.assertIn('headers', data)
        self.assertIn('X-Foo', data['headers'])

    def test_headers_case_normalized(self):
        url = _url('/headers')
        headers = {'X-FOO-bar-Baz': 'BAR'}
        response = nr.get(url, headers=headers)

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)

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

        data = json.loads(response.content)

        self.assertEqual(data, {'cookies': {'foo': 'bar'}})

    def test_receiving_cookies(self):
        url = _url('/cookies/set?foo=bar')
        response = nr.get(url, allow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.cookies, {'foo': 'bar'})


class PostTestCase(unittest.TestCase):
    def test_sending_data_dict_is_form_encoded(self):
        url = _url('/post')
        request_data = {
            'foo': 'bar baz',
        }
        response = nr.post(url, data=request_data)

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)

        self.assertEqual(data['headers']['Content-Type'], 'application/x-www-form-urlencoded')
        self.assertEqual(data['form'], request_data)

    def test_sending_data_as_bytes(self):
        url = _url('/post')
        request_data = json.dumps({'foo': 'bar'})
        headers={'Content-Type': 'application/json'}
        response = nr.post(url, data=request_data, headers=headers)

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)

        self.assertEqual(data['headers']['Content-Type'], 'application/json')
        self.assertEqual(data['data'], '{"foo": "bar"}')

    def test_json_keyword(self):
        url = _url('/post')
        json_data = {'foo': 'bar'}
        response = nr.post(url, json=json_data)

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)

        self.assertEqual(data['data'], '{"foo": "bar"}')
        self.assertEqual(data['headers']['Content-Type'], 'application/json')


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

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, '{\n  "user-agent": "%s"\n}\n' % nr._user_agent)


class CodesTestCase(unittest.TestCase):
    def test_access_status_codes_as_properies(self):
        self.assertEqual(nr.codes.ok, 200)
