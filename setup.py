from distutils.core import setup

setup(
  name = 'multilang',
  packages = ['multilang'],
  version = '0.1.3a1',
  license='MIT',
  description = 'Allows for running code in mutliple languages',
  author = 'SC van Nostrand',
  author_email = 'scvannost@gmail.com',
  download_url = 'https://github.com/scvannost/multilang/archive/0.1.3a1.tar.gz',
  url = 'https://github.com/scvannost/multilang',
  keywords = ['R', 'Matlab', 'environment', 'bash', 'multilanguage'],
  install_requires=[
      'pexpect',
      'scipy',
      'pandas',
      'numpy',
    ],
  classifiers=[
    'Development Status :: 3 - Alpha',      # Chose either "3 - Alpha", "4 - Beta" or "5 - Production/Stable" as the current state of your package
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 3',
  ],
)
