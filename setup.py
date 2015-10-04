from distutils.core import setup

import notrequests


setup(
    name='notrequests',
    version=notrequests.__version__,
    author='David Buxton',
    license='MIT',
    py_modules=['notrequests'],
)
