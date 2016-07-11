"""
Setup script for dhcpkit_looking_glass
"""
import os

from setuptools import find_packages, setup

import dhcpkit_looking_glass


# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(filename):
    """
    Read the contents of a file

    :param filename: the file name relative to this file
    :return: The contents of the file
    """
    return open(os.path.join(os.path.dirname(__file__), filename)).read()


setup(
    name='dhcpkit_looking_glass',
    version=dhcpkit_looking_glass.__version__,

    description='Looking Glass extensions to DHCPKit',
    long_description=read('README.rst'),
    keywords='dhcp server ipv6 looking-glass',
    url='https://github.com/sjm-steffann/dhcpkit_looking_glass',
    license='GPLv3',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: No Input/Output (Daemon)',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Operating System :: Unix',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet',
        'Topic :: System :: Networking',
        'Topic :: System :: Systems Administration',
    ],

    packages=find_packages(exclude=['tests', 'tests.*']),
    include_package_data=True,
    entry_points={
    },

    install_requires=[
        'django >= 1.8',
        'dhcpkit_kafka >= 0.9.0',
        'netaddr',
        'pyyaml',
        'pytz',
    ],

    test_suite='tests',

    author='Sander Steffann',
    author_email='sander@steffann.nl',

    zip_safe=False,
)
