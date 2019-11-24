"""
Renoir is a templating engine designed with simplicity in mind.


Links
-----

* `git repo <http://github.com/emmett-framework/renoir>`_

"""

import re

from setuptools import find_packages, setup

with open('renoir/__init__.py', 'r', encoding='utf8') as f:
    version = re.search(r'__version__ = "(.*?)"', f.read(), re.M).group(1)


setup(
    name='Renoir',
    version=version,
    url='http://github.com/emmett-framework/renoir',
    license='BSD-3-Clause',
    author='Giovanni Barillari',
    author_email='gi0baro@d4net.org',
    description='A templating engine designed with simplicity in mind.',
    long_description=__doc__,
    packages=find_packages(),
    python_requires='>=3.6',
    include_package_data=True,
    install_requires=[],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Text Processing :: Markup :: HTML'
    ],
    entry_points={}
)
