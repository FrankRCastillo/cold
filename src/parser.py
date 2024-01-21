import re

from urllib.parse import quote_plus
from lxml         import html

class Parse_Results:
    def __init__(self, cli, dl, config):
        self.cli    = cli
        self.dl     = dl
        self.config = config
        self.url    = config['url']
        self.params = config['params']
        self.rows   = config['rows']
        self.cols   = config['columns']
        self.link   = config['link']

    def get_results(self, query_str):
        self.cli.results = {}

        query      = quote_plus(query_str)
        req_url    = self.format_url(self.url, query)
        raw_html   = self.dl.get_url(req_url)
        tree       = html.fromstring(raw_html)
        cols_xpath = { col : self.cols[col]['xpath'] for col in self.cols if 'xpath' in self.cols[col].keys() }
        rows_tree  = tree.xpath(self.rows)
        i          = 1

        for row in rows_tree[1:]:
            tmp_dic = {}
            tmp_dic['idx'] = str(i)

            for col in cols_xpath:
                xpath_val       = cols_xpath[col]
                xpath_rslt      = row.xpath(xpath_val)[0]
                html_val        = xpath_rslt.text_content().strip()
                tmp_dic[col]    = str(html_val)
            
            tmp_dic['link_row'] = row

            self.cli.results[str(i)] = tmp_dic

            i = i + 1

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
