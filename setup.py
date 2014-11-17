from setuptools import setup, find_packages
import os

version = '0.1'

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
      install_requires=[
          'setuptools==3.6',
          'eduid_actions>=0.0.1-dev',
          'eduid-am>=0.4.9-dev',
          'jinja2==2.7.3',
          'pwgen==0.4',
          'vccs_client>=0.4.1',
      ],
      entry_points="""
        [eduid_actions.action]
            change_passwd = eduid_action.change_passwd:ChangePasswdPlugin
      """,
      )
