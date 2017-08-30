from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(name='ananas',
      version='1.0.0a1',
      description='Mastodon bot framework built on Mastodon.py',
      long_description=long_description,
      author='Andrew Chronister',
      author_email='chr@cybre.space',
      license='MIT',
      keywords='mastodon microblogging bot',
      url='https://github.com/chronister/ananas',
      classifiers=[
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'Topic :: Communications',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3',
      ],

      packages=find_packages(exclude=['custom']),
      entry_points={
          'console_scripts': [
              'ananas=run:main',
          ],
      },
      package_data={
          'sample': ['package_data.dat'],
      },
      install_requires=['requests', 'more_itertools', 'Mastodon.py'],
      python_requires='~=3',
)
