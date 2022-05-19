import fnmatch

from setuptools import find_packages, setup
from setuptools.command.build_py import build_py as build_py_orig


def readme():
    with open('README.md') as f:
        return f.read()


excluded = ['mobiledna/communication/config.py']


class build_py(build_py_orig):
    def find_package_modules(self, package, package_dir):
        modules = super().find_package_modules(package, package_dir)
        print('HERE', modules)
        return [
            (pkg, mod, file)
            for (pkg, mod, file) in modules
            if not any(fnmatch.fnmatchcase(file, pat=pattern) for pattern in excluded)
        ]


setup(
    packages=find_packages(),
    cmdclass={'build_py': build_py},
    name='mobiledna',
    version='0.7.1',
    description='Codebase in support of mobileDNA platform',
    long_description='mobileDNA is a __data__ logging app that sheds '
                     'light on smartphone usage. Data collected '
                     'through the app can be analysed using this '
                     'package, which contains communication scripts '
                     '(to communicate with the server), basic and advanced '
                     'analytic functionality, and visual dashboards.',
    url='https://github.ugent.be/imec-mict-UGent/mobiledna_py',
    author='Kyle Van Gaeveren & Wouter Durnez',
    author_email='Wouter.Durnez@UGent.be',
    license='MIT',
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
        # 'pyarrow',
        'holidays',
        'bs4'
    ],
    include_package_data=True,
    zip_safe=False)
