from setuptools import setup, find_packages

setup( name = 'cold'
     , version = '1.0.0'
     , description = 'CoLD: Command Line Downloader. Scrape websites and download files from the command line.'
     , packages = find_packages()
     , include_package_data = True
     , install_requires = [ 'lxml>=4.0.0'
                          , 'requests>=2.0.0'
                          ]
     , entry_points = { 'console_scripts': [ 'cold=cold_module.cold:main'
                                           ]
                      ,
                      }
     , url = "https://github.com/FrankRCastillo/cold"
     )
