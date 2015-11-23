from setuptools import setup, find_packages
import os


version = '0.1.0'

requires = [
    'setuptools>=18.5',
    'eduid_actions>=0.0.1',
    'eduid-common>=0.1.0',
    'pwgen==0.4',
]

test_requires = [
    'WebTest==2.0.18',
    'mock==1.0.1',
]

testing_extras = test_requires + [
    'nose==1.3.7',
    'coverage==4.0',
    'nosexcover==1.0.10',
]

long_description = (
    open('README.txt').read()
    + '\n' +
    'Contributors\n'
    '============\n'
    + '\n' +
    open('CONTRIBUTORS.txt').read()
    + '\n' +
    open('CHANGES.txt').read()
    + '\n')

setup(name='eduid_action.change_passwd',
      version=version,
      description="Change password plugin for eduid-actions",
      long_description=long_description,
      # Get more strings from
      # http://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        "Programming Language :: Python",
        ],
      keywords='',
      author='Enrique Perez Arnaud',
      author_email='enrique@cazalla.net',
      url='https://github.com/SUNET/',
      license='gpl',
      packages=find_packages('src'),
      package_dir = {'': 'src'},
      namespace_packages=['eduid_action'],
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=test_requires,
      extras_require={
          'testing': testing_extras,
      },
      entry_points={
          'eduid_actions.action':
                    ['change_passwd = eduid_action.change_passwd.action:ChangePasswdPlugin'],
          'eduid_am.attribute_fetcher':
                    ['change_passwd = eduid_action.change_passwd.am:attribute_fetcher'],
          'eduid_am.plugin_init':
                    ['change_passwd = eduid_action.change_passwd.am:plugin_init'],
          },
      )
