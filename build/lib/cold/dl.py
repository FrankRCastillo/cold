import os
import requests
import socket
import time
import urllib3
import urllib.error

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
        self.timeout     = cli.config.get('timeout', 20)
        self.connect_timeout = cli.config.get('connect-timeout', self.timeout)
        self.read_timeout = cli.config.get('read-timeout', self.timeout)
        self.size        = 0
        self.get_success = False

    def get_url(self, url):
        req = Request( url
                     , data = None
                     , headers = self.hdr
                     )

        try:
            with urlopen(req, timeout=self.timeout) as response:
                content  = response.read()
                encoding = response.headers.get_content_charset('utf-8')
                text     = content.decode(encoding)

                return text
        except (urllib.error.URLError, socket.timeout, TimeoutError, OSError) as e:
            self.cli.set_status(f'Error fetching URL (timeout): {e}')
            self.cli.show_results()
            return ""

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

            total = 0
            head_req = None

            try:
                head_req = sess.head(url, allow_redirects=True, timeout=(self.connect_timeout, self.read_timeout))
                head_req.raise_for_status()
                total = int(head_req.headers.get('Content-Length', 0))

            except requests.exceptions.RequestException as e:
                self.cli.set_status(f'HEAD failed, continuing with GET: {e}')
                self.cli.show_results()

            name_url = head_req.url if head_req is not None else url
            fullpath = self.get_url_filename(name_url)
            exist_size = 0

            if path.exists(fullpath):
                exist_size = path.getsize(fullpath)

                if total > 0 and exist_size == total:
                    self.cli.set_status(f'File exists: {fullpath}.')
                    return

                if exist_size > 0:
                    file_mode = 'ab'

            if exist_size > 0:
                sess.headers['Range'] = f'bytes={exist_size}-'
            else:
                sess.headers.pop('Range', None)

            last_pct = 0
            last_progress = 0
            progress_step = 1024 * 64

            while max_retry > cnt_retry:
                try:
                    rsp = sess.get(url, stream=True, timeout=(self.connect_timeout, self.read_timeout))
                    rsp.raise_for_status()

                    if exist_size > 0 and rsp.status_code == 200:
                        exist_size = 0
                        file_mode = 'wb'
                        sess.headers.pop('Range', None)

                    if total == 0:
                        total = int(rsp.headers.get('Content-Length', 0))

                    final_fullpath = self.get_url_filename(rsp.url)

                    if final_fullpath != fullpath:
                        if exist_size > 0 and path.exists(fullpath) and not path.exists(final_fullpath):
                            os.rename(fullpath, final_fullpath)

                        fullpath = final_fullpath

                        if path.exists(fullpath):
                            exist_size = path.getsize(fullpath)

                            if total > 0 and exist_size == total:
                                self.cli.set_status(f'File exists: {fullpath}.')
                                return

                            file_mode = 'ab' if exist_size > 0 else 'wb'

                    self.progress_bar(exist_size, total)

                    with open(fullpath, file_mode) as f:
                        for data in rsp.iter_content(chunk_size=1024):
                            if not data:
                                continue

                            if self.cli.end_prog or self.cli.poll_escape():
                                self.cli.set_status('Download cancelled.')
                                self.cli.show_results()
                                return

                            exist_size += f.write(data)

                            if total > 0:
                                curr_pct = 100 * exist_size / total

                                if curr_pct - last_pct >= 0.1:
                                    self.progress_bar(exist_size, total)
                                    last_pct = curr_pct

                            elif exist_size - last_progress >= progress_step:
                                self.progress_bar(exist_size, total)
                                last_progress = exist_size

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
        if denom <= 0:
            message = f'Downloading {numer:,} bytes'
            total_len = self.cli.term_wdt - len(message) - 3

            if total_len > 3:
                progr_len = min(total_len, 10)
                total_bar = "." * (total_len - progr_len)
                progr_bar = "=" * progr_len
                self.cli.cprint(f'{message} [{progr_bar}{total_bar}]', new_line = False)
            else:
                self.cli.cprint(message, new_line = False)

            return

        denom     = max(denom, 1)
        frac      = min(numer / denom, 1)
        percent   = round(frac * 100, 1)
        message   = f'Downloading {numer:,}/{denom:,} bytes | {percent}%'
        total_len = self.cli.term_wdt - len(message) - 5
        total_len = 1 if total_len < 1 else total_len
        progr_len = int(frac * total_len)
        trail_len = total_len - progr_len
        total_bar = "." * trail_len
        progr_bar = "=" * progr_len

        self.cli.cprint(f'{message} [{progr_bar}>{total_bar}]', new_line = False)
