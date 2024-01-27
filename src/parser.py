import re

from urllib.parse import quote_plus
from lxml         import html

class Parse_Results:
    def __init__(self, cli, dl):
        self.cli        = cli
        self.dl         = dl
        self.config     = cli.config
        self.url        = cli.config['url']
        self.params     = cli.config['params']
        self.rows       = cli.config['rows']
        self.cols       = cli.config['columns']
        self.link       = cli.config['link']
        self.xpaths     = { col : self.cols[col]['xpath'] for col in self.cols if 'xpath' in self.cols[col].keys() }
        self.results    = dict()
        self.result_ids = set()

    def get_results(self):
        query    = quote_plus(self.cli.query)
        idx_col  = self.cli.idx_col
        key_col  = self.cli.key_col
        max_rows = self.cli.max_rows
        rslt_cnt = len(self.results)
        idx_val  = 1

        while rslt_cnt < max_rows * self.cli.win_page:
            req_url   = self.format_url(self.url, query)
            raw_html  = self.dl.get_url(req_url)
            tree      = html.fromstring(raw_html)
            rows_tree = tree.xpath(self.rows)

            if not rows_tree or len(rows_tree) == 1:
                self.cli.last_page = self.cli.win_page if self.cli.win_page > self.cli.last_page else self.cli.last_page
                break
            else:
                self.cli.last_page = self.cli.win_page + 1 if len(self.results) > len(self.cli.results) else self.cli.win_page

            start_row = 1 if self.cli.config['skip-header'] else 0

            for idx_val, row in enumerate(rows_tree[start_row:], start = rslt_cnt + 1):
                idx_str = str(idx_val)
                tmp_dic = {idx_col : idx_str}
                key_val = None

                for k, v in self.xpaths.items():
                    xpath_rslt = row.xpath(v)[0]
                    html_val   = str(xpath_rslt.text_content().strip())
                    tmp_dic[k] = html_val

                    if k == key_col:
                        key_val = html_val
                    
                if key_val and key_val not in self.result_ids:
                    self.result_ids.add(key_val)
                    tmp_dic['link_row']   = row
                    self.results[idx_str] = tmp_dic

            rslt_cnt = len(self.results)
            self.cli.params['page'][0] += 1

        rcrd_min = max_rows * (self.cli.win_page - 1) 
        rcrd_max = min(rcrd_min + max_rows, rslt_cnt)
        
        return dict(list(self.results.items())[rcrd_min:rcrd_max])

    def reset_results(self):
        self.results    = dict()
        self.result_ids = set()

    def get_link(self, row, link_xpaths):
        url = None
        i   = 0

        for xpath in link_xpaths:
            if i == 0:
                url = row.xpath(xpath)[0]

            else:
                page = self.dl.get_url(url)
                tree = html.fromstring(page)
                url  = tree.xpath(xpath)[0]

            i = i + 1

        return url            

    def format_url(self, url, query):
        pattern  = r'\{(\w+)\}'
        url_keys = re.findall(pattern, url)
        url_dict = {}

        for url_key in url_keys:
            if url_key == 'query':
                url_dict[url_key] = query

            else:
                url_dict[url_key] = self.params[url_key][0]

        return url.format(**url_dict)
