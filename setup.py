from setuptools import setup, find_packages

setup(
    name='cold',
    version='1.0.0',
    description='CoLD: Command Line Downloader. Scrape websites and download files from the command line.',
    packages=find_packages(),
    include_package_data=True,
    package_data={'cold': ['config/*']},  # Ensure this directory exists
    install_requires=[
        'lxml>=4.6.0',
        'requests>=2.25.0',
        'wcwidth>=0.2.5',
    ],
    entry_points={
        'console_scripts': ['cold=cold.cold:main']
    },
    url="https://github.com/FrankRCastillo/cold"
)

