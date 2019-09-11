from setuptools import setup


def readme():
    with open('README.md') as f:
        return f.read()


setup(name='mobiledna',
      version='0.01',
      description='Codebase in support of mobileDNA platform',
      url='https://github.ugent.be/imec-mict-UGent/mobiledna_py',
      author='Kyle Van Gaeveren & Wouter Durnez',
      author_email='Kyle.VanGaeveren@UGent.be',
      license='MIT',
      packages=['mobiledna'],
      install_requires=[
          'numpy',
          'pandas',
          'tqdm',
          'matplotlib'
      ],
      zip_safe=False)