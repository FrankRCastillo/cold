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
        self.results    = {}
        self.result_ids = set()
        self.win_page   = 1

    def get_results(self, query_str):
        id_col   = self.cli.id_col
        rslt_cnt = len(self.results.keys())
        query    = quote_plus(query_str)
        max_rows = self.cli.max_rows
        i        = 1

        while rslt_cnt < max_rows * self.win_page:
            req_url    = self.format_url(self.url, query)
            raw_html   = self.dl.get_url(req_url)
            tree       = html.fromstring(raw_html)
            rows_tree  = tree.xpath(self.rows)
            start_row  = 1 if self.cli.config['skip-header'] else 0

            for row in rows_tree[start_row:]:
                tmp_dic = {}

                for k, v in self.xpaths.items():
                    xpath_rslt = row.xpath(v)[0]
                    html_val   = xpath_rslt.text_content().strip()
                    tmp_dic[k] = str(html_val)
                
                tmp_dic['link_row'] = row
                id_val = tmp_dic[id_col]

                if id_val not in self.result_ids:
                    self.result_ids.add(id_val)
                    self.results[id_val] = tmp_dic

                    i = i + 1

            self.cli.params['page'][0] += 1

            rslt_cnt = len(self.results.keys())

        rcrd_min = max_rows * (self.win_page - 1) 
        rcrd_max = min(rcrd_min + max_rows, rslt_cnt)

        self.cli.results = dict(list(self.results.items())[rcrd_min:rcrd_max])

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

    def get_keys(self, string):
        pattern = r'\{(\w+)\}'

        return re.findall(pattern, string)

    def format_url(self, url, query):
        url_keys = self.get_keys(url)
        url_dict = {}

        for url_key in url_keys:
            if url_key == 'query':
                url_dict[url_key] = query

            else:
                url_dict[url_key] = self.params[url_key][0]

        return url.format(**url_dict)
