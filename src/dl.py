import os
import requests
import time
import urllib3

from os                 import path
from urllib.parse       import unquote
from urllib.parse       import urlparse
from urllib.parse       import urlunparse
from urllib.request     import urlopen
from urllib.request     import Request
from urllib3.exceptions import InsecureRequestWarning

class Downloader:
    def __init__(self, cli):
        self.cli         = cli
        self.download    = cli.config['download']
        self.user_agent  = cli.config['user-agent']
        self.hdr         = { 'User-Agent'    : self.user_agent
                           , 'Cache-Control' : 'no-cache'
                           }
        self.size        = 0
        self.get_success = False

    def get_url(self, url):
        req = Request( url
                     , data = None
                     , headers = self.hdr
                     )

        with urlopen(req) as response:
            content  = response.read()
            encoding = response.headers.get_content_charset('utf-8')
            text     = content.decode(encoding)

            return text

    def get_url_filename(self, url):
        parsed_url = urlparse(url)
        basename   = path.basename(parsed_url.path)
        fullpath   = unquote(path.join(self.download, basename))

        return fullpath

    def get_file(self, url):
        self.get_success = False

        if type(url) != str:
            self.cli.set_status(f"Error downloading {url}")
            self.cli.show_results()

            return

        url        = self.absolute_url(url)
        file_mode  = 'wb'
        max_retry  = 5
        cnt_retry  = 0

        urllib3.disable_warnings(InsecureRequestWarning)

        self.cli.set_status(f'Downloading #{self.cli.user_input}: {url}')
        self.cli.show_results()

        with requests.Session() as sess:
            sess.headers.update(self.hdr)
            sess.verify = self.cli.ssl_verify

            head_req = None
            
            try:
                head_req = sess.head(url)

            except Exception as e:
                self.cli.set_status(f'Error downloading: {e}')
                return

            head_req.raise_for_status()
            total = int(head_req.headers.get('Content-Length', 0))

            fullpath = self.get_url_filename(url)

            if path.exists(fullpath):
                exist_size = path.getsize(fullpath)

                if exist_size == total:
                    self.cli.set_status(f'File exists: {fullpath}.')
                    return
            
                file_mode = 'ab'

            else:
                exist_size = 0

            sess.headers['Range'] = f'bytes={exist_size}-'

            while max_retry > cnt_retry:
                try:
                    rsp = sess.get(url, stream=True)
                    rsp.raise_for_status()

                    self.progress_bar(exist_size, total)

                    fullpath = self.get_url_filename(rsp.url)
                    temppath = f'{fullpath}.tmp'

                    with open(temppath, file_mode) as f:
                        for data in rsp.iter_content(chunk_size=1024):
                            size = exist_size + f.write(data)
                            exist_size = size
                            
                            self.progress_bar(exist_size, total)

                    os.rename(temppath, fullpath)

                    self.cli.set_status(f'Downloaded #{self.cli.user_input}: {fullpath}')
                    self.cli.show_results()                                        

                    return  # Download complete, exit function

                except requests.exceptions.RequestException as e:
                    cnt_retry += 1
                    self.cli.set_status(f'Error downloading {fullpath}, retrying ({cnt_retry}/{max_retry}): {e}')
                    self.cli.show_results()
                    time.sleep(2 ** cnt_retry)  # Exponential backoff

        self.cli.set_status(f'Failed to download {fullpath} after {max_retry} retries')
        self.cli.show_results()

    def absolute_url(self, url):
        parsed_url = urlparse(url)

        if bool(parsed_url.scheme) or bool(parsed_url.netloc):
            return url

        else:
            parsed_parent_url = urlparse(self.cli.url)
            parent_scheme     = str(parsed_parent_url.scheme)
            parent_netloc     = str(parsed_parent_url.netloc)
            construct_url     = urlunparse((parent_scheme, parent_netloc, url, '', '', ''))

            return construct_url

    def progress_bar(self, numer, denom):
        denom     = 1 if denom == 0 else denom
        frac      = numer / denom
        percent   = round(frac * 100, 1)
        message   = f'Downloading {numer:,}/{denom:,} bytes | {percent}%'
        total_len = self.cli.term_wdt - len(message) - 5
        progr_len = int( frac * total_len )
        trail_len = total_len - progr_len
        total_bar = "." * trail_len
        progr_bar = "=" * progr_len

        self.cli.cprint(f'{message} [{progr_bar}>{total_bar}]', new_line = False)
