import requests
import time

from os           import path
from urllib.parse import unquote
from urllib.parse import urlparse
from requests.packages.urllib3.exceptions import InsecureRequestWarning

class Downloader:
    def __init__(self, cli):
        self.cli        = cli
        self.download   = cli.config['download']
        self.user_agent = cli.config['user-agent']
        self.hdr        = { 'User-Agent' : self.user_agent }
        self.size       = 0

    def get_url(self, url):
        req = requests.get(url, headers = self.hdr)

        return req.content

    def get_file(self, url):
        parsed_url = urlparse(url)
        basename   = path.basename(parsed_url.path)
        filename   = unquote(path.join(self.download, basename))
        file_mode  = 'wb'
        max_retry  = 5
        cnt_retry  = 0

        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

        with requests.Session() as sess:
            sess.headers.update(self.hdr)
            sess.verify = self.cli.ssl_verify

            # Initial request to get file size on server

            head_req = None
            
            try:
                head_req = sess.head(url)

            except Exception as e:
                self.cli.set_last_msg(f'Error downloading: {e}')
                return

            head_req.raise_for_status()
            total = int(head_req.headers.get('Content-Length', 0))

            if path.exists(filename):
                exist_size = path.getsize(filename)

                if exist_size == total:
                    self.cli.set_last_msg(f'{basename} already fully downloaded.')
                    return
            
                file_mode = 'ab'

            else:
                exist_size = 0

            sess.headers['Range'] = f'bytes={exist_size}-'

            while max_retry > cnt_retry:
                try:
                    req = sess.get(url, stream=True)
                    req.raise_for_status()

                    self.progress_bar(exist_size, total)

                    with open(filename, file_mode) as f:
                        for data in req.iter_content(chunk_size=1024):
                            size = exist_size + f.write(data)
                            exist_size = size
                            self.progress_bar(exist_size, total)

                    self.cli.set_last_msg(f'Downloaded {filename}')
                    return  # Download complete, exit function

                except requests.exceptions.RequestException as e:
                    cnt_retry += 1
                    self.cli.set_last_msg(f'Error downloading {filename}, retrying ({cnt_retry}/{max_retry}): {e}')
                    time.sleep(2 ** cnt_retry)  # Exponential backoff

        self.cli.set_last_msg(f'Failed to download {filename} after {max_retry} retries')

    def progress_bar(self, numer, denom):
        frac      = numer / denom
        percent   = round(frac * 100, 1)
        message   = f'Downloading {numer:,}/{denom:,} bytes | {percent}%'
        total_len = self.cli.term_wdt - len(message) - 5
        progr_len = int( frac * total_len )
        trail_len = total_len - progr_len
        total_bar = "." * trail_len
        progr_bar = "=" * progr_len

        self.cli.cprint(f'\r{message} [{progr_bar}>{total_bar}]')
