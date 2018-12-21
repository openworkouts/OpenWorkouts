import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.txt')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()

requires = [
    'plaster_pastedeploy',
    'pyramid',
    'pyramid_chameleon',
    'pyramid_debugtoolbar',
    'pyramid_retry',
    'pyramid_tm',
    'pyramid_zodbconn',
    'transaction',
    'ZODB3',
    'waitress',
    'repoze.folder',
    'repoze.catalog==0.8.4',
    'bcrypt',
    'FormEncode',
    'pyramid_simpleform==0.7dev0',  # version needed for python3
    'unidecode',
    'gpxpy',
    'lxml',
    'pytz'
]

tests_require = [
    'WebTest >= 1.3.1',  # py3 compat
    'pytest',
    'pytest-cov',
    'pytest-flakes',
    'pytest-xdist',
    'pytest-codestyle',
]

dependency_links = [
    'git+https://github.com/WuShell/repoze.catalog.git@0.8.4'
    '#egg=repoze.catalog-0.8.4'
]

setup(
    name='ow',
    version='0.1',
    description='OpenWorkouts, tracking your workouts openly',
    long_description=README + '\n\n' + CHANGES,
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Pyramid',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
    ],
    author='Francisco de Borja Lopez Rio',
    author_email='borja@codigo23.net',
    url='https://openworkouts.org',
    keywords='web pyramid pylons',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    dependency_links=dependency_links,
    extras_require={
        'testing': tests_require,
    },
    install_requires=requires,
    entry_points={
        'paste.app_factory': [
            'main = ow:main',
        ],
    },
)
