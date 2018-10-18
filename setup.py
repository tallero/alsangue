from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name = "alsangue",
    version = "0.2",
    author = "Pellegrino Prevete",
    author_email = "pellegrinoprevete@gmail.com",
    description = "naive static website builder",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url = "https://github.com/tallero/alsangue",
    packages = find_packages(),
    package_data = {
    
    },
    include_package_data=True,
    entry_points = {
        'console_scripts': ['alsangue = alsangue:main']
    },
    install_requires = [
    'setproctitle',
    'beautifulsoup4',
    ],
    classifiers = [
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: Unix",
    ],
)
