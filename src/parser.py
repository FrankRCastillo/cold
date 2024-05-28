import re

from urllib.parse import quote_plus
from urllib.parse import urlparse
from urllib.parse import urlunparse
from lxml         import html

class Parse_Results:
    def __init__(self, cli, dl):
        self.cli         = cli
        self.dl          = dl
        self.config      = cli.config
        self.url         = cli.config['url']
        self.params      = cli.config['params']
        self.rows        = cli.config['rows']
        self.cols        = cli.config['columns']
        self.link        = cli.config['link']
        self.page_params = cli.config['page-params']
        self.xpaths      = { col : self.cols[col]['xpath'] for col in self.cols if 'xpath' in self.cols[col].keys() }
        self.results     = dict()
        self.result_ids  = set()

    def get_results(self):
        query    = quote_plus(self.cli.query)
        idx_col  = self.cli.idx_col
        key_col  = self.cli.key_col
        max_rows = self.cli.max_rows
        rslt_cnt = len(self.results)
        idx_val  = 1

        page_param_name = self.page_params['name']
        page_param_step = self.page_params['step']

        while rslt_cnt < max_rows * self.cli.win_page:
            req_url   = self.format_url(self.url, query)
            raw_html  = self.dl.get_url(req_url)
            tree      = html.fromstring(raw_html)
            rows_tree = tree.xpath(self.rows)

            if not isinstance(rows_tree, list) or len(rows_tree) == 0:
                break

            rows_len  = len(rows_tree) if isinstance(rows_tree, list) else 1
            start_row = 1 if self.cli.config['skip-header'] else 0

            if not rows_tree or rows_len == 1:
                self.cli.last_page = self.cli.win_page - 1 if self.cli.win_page > self.cli.last_page else self.cli.last_page
                break

            rows_enum = enumerate(rows_tree[start_row:], start = rslt_cnt + 1)

            for idx_val, row in rows_enum:
                idx_str = str(idx_val)
                tmp_dic = {idx_col : idx_str}
                key_val = None

                for k, v in self.xpaths.items():
                    xpath_obj = row.xpath(v)
                    html_val  = ""
                    
                    if xpath_obj:
                        if isinstance(xpath_obj, list):
                            if isinstance(xpath_obj[0], html.HtmlElement):
                                xpath_itr = xpath_obj[0].itertext()
                                xpath_arr = [val.strip() for val in xpath_itr]
                                html_val  = " ".join(xpath_arr)

                            else:
                                html_val  = str(xpath_obj[0]).strip()

                    html_val = re.sub(r'[^\S ]+', '', html_val)

                    tmp_dic[k] = html_val

                    if k == key_col:
                        key_val = html_val

                if key_val and key_val not in self.result_ids:
                    self.result_ids.add(key_val)

                    tmp_dic['link_row']   = row
                    self.results[idx_str] = tmp_dic

            rslt_cnt = len(self.results)
            self.cli.params[page_param_name] += page_param_step

        rcrd_min = max_rows * (self.cli.win_page - 1) 
        rcrd_max = min(rcrd_min + max_rows, rslt_cnt)
        
        return dict(list(self.results.items())[rcrd_min:rcrd_max])

    def reset_results(self):
        self.results    = dict()
        self.result_ids = set()

    def get_link(self, row, link_xpaths):
        url = None

        for idx, xpath in enumerate(link_xpaths):
            if idx == 0 or len(link_xpaths) == 1:
                url = str(row.xpath(xpath)[0])

            elif '{path}' in xpath:
                url_parse = urlparse(url)
                url_path  = urlunparse(( ''
                                       , ''
                                       , url_parse.path
                                       , url_parse.params
                                       , url_parse.query
                                       , url_parse.fragment
                                       ))
                url_path = url_path.lstrip('/')
                url      = f'{xpath}'.format(path = url_path)

            else:
                page = self.dl.get_url(url)
                tree = html.fromstring(page)
                elem = tree.xpath(xpath)

                if isinstance(elem, list) and len(elem) > 0:
                    url = str(elem[0])
        
        return url            

    def format_url(self, url, query):
        pattern  = r'\{(\w+)\}'
        url_keys = re.findall(pattern, url)
        url_dict = {}

        for url_key in url_keys:
            if url_key == 'query':
                url_dict[url_key] = query

            else:
                param_val = None

                if type(self.params[url_key]) == list:
                    param_val = self.params[url_key][0]

                else:
                    param_val = self.params[url_key]


                url_dict[url_key] = param_val

        return url.format(**url_dict)

    def write_file(self, path, text):
        text_nl = f'{text}\n'

        with open(path, 'a') as file: 
            file.write(text_nl)
