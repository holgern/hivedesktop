import os
import setuptools
from src.main.python.hivedesktop import VERSION

with open("README.md", "r") as fh:
    long_description = fh.read()


class CleanCommand(setuptools.Command):
    """Custom clean command to tidy up the project root."""
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        os.system('git clean -xdf ./src/main')


PY_SRC_PATH = "src/main/python"


setuptools.setup(
    name="hivedesktop",
    version=VERSION,
    author="holger80",
    author_email="holgernahrstaedt@gmx.de",
    description=("Fetches your Amazon order history and matching/tags your "
                 "Mint transactions"),
    keywords='hive blockchain pyqt desktop app',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/holgern/hivedesktop",
    license='GPLv3',
    package_dir={"": PY_SRC_PATH},
    packages=setuptools.find_packages(where=PY_SRC_PATH),
    python_requires='>=3',
    classifiers=[
        "Programming Language :: Python :: 3",
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        "Operating System :: OS Independent",
        "Topic :: Office/Business :: Financial",
    ],
    # Note: this is a subset of the fbs requirements; only what's needed to
    # directly launch the gui or cli from python.
    install_requires=[        
        'PyQt5==5.14.2',
        'PyQtWebEngine==5.14',
        'markdown',
        'Pygments',
        'mdx_smartypants',
        'dataset',
        'deepdish',
        'jinja2',
        'markupsafe',
        'pymdown-extensions',
        'beem',
        'cryptography',
        'pycryptodome',
        'python-dateutil'
    ],
    entry_points=dict(
        console_scripts=[
            'hivedesktop=hivedesktop.main:main',
        ],
    ),
    cmdclass={
        'clean': CleanCommand,
    },
)
