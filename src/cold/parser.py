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
        self.page_size   = None

    def get_page_span(self, max_rows):
        if self.page_size is None:
            return max_rows

        return self.page_size if self.page_size <= max_rows else max_rows

    def get_results(self):
        query    = quote_plus(self.cli.query)
        idx_col  = self.cli.idx_col
        key_col  = self.cli.key_col
        max_rows = self.cli.max_rows
        rslt_cnt = len(self.results)
        idx_val  = 1

        page_param_name = self.page_params['name']
        page_param_step = self.page_params['step']
        page_param_base = self.cli.get_param_base(page_param_name)
        page_span = self.get_page_span(max_rows)
        total_needed = page_span * self.cli.win_page if self.page_size is not None else None

        while True:
            if self.cli.end_prog:
                break

            if self.cli.poll_escape():
                break

            if total_needed is not None and rslt_cnt >= total_needed:
                break

            page_val = self.cli.params.get(page_param_name, page_param_base)
            page_num = 1

            try:
                if page_param_step:
                    page_num = int((page_val - page_param_base) / page_param_step) + 1
            except Exception:
                page_num = 1

            self.cli.set_status(f'Loading page {page_num}...')
            self.cli.show_results()

            req_url   = self.format_url(self.url, query)
            raw_html  = self.dl.get_url(req_url)
            if not raw_html:
                break
            tree      = html.fromstring(raw_html)
            rows_tree = tree.xpath(self.rows)

            if not isinstance(rows_tree, list):
                rows_tree = [rows_tree]

            rows_len = len(rows_tree)

            if rows_len == 0:
                break

            start_row = 1 if self.cli.config['skip-header'] else 0

            if rows_len <= start_row:
                self.cli.last_page = self.cli.win_page - 1 if self.cli.win_page > self.cli.last_page else self.cli.last_page
                break

            page_rows = rows_len - start_row

            if page_rows > 0 and self.page_size is None:
                self.page_size = page_rows

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
                        else:
                            html_val = str(xpath_obj).strip()

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

            page_span = self.get_page_span(max_rows)
            total_needed = page_span * self.cli.win_page
            progress_count = min(rslt_cnt, total_needed)
            self.cli.set_status(f'Loaded {progress_count}/{total_needed} results...')
            self.cli.show_results()

        page_span = self.get_page_span(max_rows)
        rcrd_min = page_span * (self.cli.win_page - 1)
        rcrd_max = min(rcrd_min + page_span, rslt_cnt)
        
        return dict(list(self.results.items())[rcrd_min:rcrd_max])

    def reset_results(self):
        self.results    = dict()
        self.result_ids = set()
        self.page_size  = None

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
                if not page:
                    break
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
