from setuptools import setup

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