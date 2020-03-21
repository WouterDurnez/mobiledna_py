import setuptools
from setuptools import setup


def readme():
    with open('README.md') as f:
        return f.read()


setup(name='mobiledna',
      version='0.3',
      description='Codebase in support of mobileDNA platform',
      long_description='mobileDNA is a data logging app that sheds '
                       'light on smartphone usage. Data collected '
                       'through the app can be analysed using this '
                       'package, which contains communication scripts '
                       '(to communicate with the server), basic and advanced '
                       'analytic functionality, and visual dashboards.',
      url='https://github.ugent.be/imec-mict-UGent/mobiledna_py',
      author='Kyle Van Gaeveren & Wouter Durnez',
      author_email='Wouter.Durnez@UGent.be',
      license='MIT',
      packages=setuptools.find_packages(),
      classifiers=[
          "Programming Language :: Python :: 3",
          "License :: OSI Approved :: MIT License",
          "Operating System :: OS Independent",
      ],
      install_requires=[
          'numpy',
          'pandas',
          'tqdm',
          'matplotlib',
          'elasticsearch<=6.3.1',
          'pyarrow'
      ],
      zip_safe=False)
