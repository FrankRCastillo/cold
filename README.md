# CoLD
Command Line Downloader

CoLD is a Python-based command-line tool used to download files from websites showing data in table-based form. The project started as a scraper for Libgen.is, the online book respoistory. Libgen and other pages can be specified using JSON config files.

![image](https://github.com/user-attachments/assets/916ab001-26f5-4bd1-8d5b-edd7a2c05920)

## Installation
1. Ensure Python 3.7 or higher is installed.
2. Clone the repository:
```
https://github.com/FrankRCastillo/cold.git
```
3. Install required dependencies:
```
pip install -r requirements.txt
```

## Usage
To start the program, run as follows:

```
python cold.py <config name> <query>
```

## Example
To use the Libgen configuraiton, run as follows:
```
python cold.py libgen "The C Programming Language"
```
