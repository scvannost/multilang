from distutils.core import setup
setup(
  name = 'matrython',
  packages = ['matrython'],
  version = '0.1.0a1',
  license='MIT',
  description = 'Allows for running R and Matlab code',
  author = 'SC van Nostrand',
  author_email = 'scvannost@gmail.com',
  download_url = 'https://github.com/scvannost/rython/archive/0.1.0.tar.gz',
  keywords = ['R', 'Matlab', 'environment'],
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
    'Programming Language :: Python :: 3.6',
  ],
)
