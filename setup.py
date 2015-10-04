from distutils.core import setup

import notrequests


setup(
    name='notrequests',
    version=notrequests.__version__,
    description='Like Requests, but using urllib2.',
    long_description='A Python wrapper for the built-in urllib2 module, compatible with Requests, intended for use on Google App Engine.',
    url = 'https://github.com/davidwtbuxton/notrequests',
    author='David Buxton',
    license='MIT',
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
    ],
    py_modules=['notrequests'],
)
