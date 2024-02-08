import curses
import math
import re

from src.dl     import Downloader
from src.parser import Parse_Results

class Interface:
    def __init__(self, config, query):
        self.config      = config
        self.url         = config['url']
        self.params      = config['params']
        self.link_xpath  = config['link']
        self.download    = config['download']
        self.ssl_verify  = config['ssl-verify']
        self.ssl_warn    = '!!! SSL VERIFICATION IS DISABLED !!! ' if not self.ssl_verify else ''
        self.key_col     = self.set_key_col(config['columns'])
        self.idx_col, self.cols = self.set_idx_col(config['columns'])
        self.col_lbl     = list(self.cols.keys())
        self.col_aln     = [ col['align'] for col in self.cols.values() ]
        self.col_wdt     = [ col['width'] for col in self.cols.values() ]
        self.query       = query
        self.search_msg  = f'Search results: {query}'
        self.user_input  = None
        self.results     = dict()
        self.results_len = 0
        self.end_prog    = False
        self.win_page    = 1
        self.last_page   = 1
        self.back_key    = [ curses.KEY_BACKSPACE, 127, 8, 263 ]
        self.key_cmds    = { curses.KEY_HOME  : self.home
                           , curses.KEY_END   : self.end
                           , curses.KEY_PPAGE : self.pgup
                           , curses.KEY_NPAGE : self.pgdn
                           , curses.KEY_F1    : self.help
                           , curses.KEY_F2    : self.set_params
                           , 27               : self.quit
                           }
        self.help_list   = [ f'{self.idx_col}<Enter> Download'
                           , 'query<Enter> Search'
                           , '<home> First'
                           , '<pgup> Prev'
                           , '<pgdn> Next'
                           , '<F1> Help'
                           , '<F2> Parameters'
                           , '<Esc> Quit'
                           ]
        self.help_msg    = ", ".join(self.help_list)

    def start_interface(self, stdscr):
        self.stdscr = stdscr

        self.set_row_params()

        self.dl     = Downloader(self)
        self.parser = Parse_Results(self, self.dl)

        curses.start_color()
        self.load_results()
        self.show_results()

        while not self.end_prog:
            self.user_input = self.cinput(self.input_msg)
            
            if self.end_prog:
                break

            if self.user_input in self.results.keys():
                url = self.results[self.user_input].get('link')

                if not url:
                    link_row = self.results[self.user_input]['link_row']
                    self.results[self.user_input]['link'] = self.parser.get_link(link_row, self.link_xpath)
                    url = self.results[self.user_input]['link']

                self.dl.get_file(url)

            elif self.user_input != '':
                self.query             = self.user_input
                self.win_page          = 1
                self.last_page         = 1
                self.params['page'][0] = 1

                self.parser.reset_results()
                self.set_status(f'Searching for {self.query}...')
                self.show_results()
                self.load_results()
                self.show_results()

        curses.echo()
        curses.endwin()

    def show_results(self):
        self.stdscr.clear()
        self.update_column_align()
        self.update_column_width()

        rslt_list = list(self.results.keys())
        rslt_len  = len(rslt_list)
        rslt_max  = 3 if rslt_len == 0 else int(rslt_list[-1])
        idx_wdt   = int(math.log(rslt_max, 10) + 2)
        self.cols[self.idx_col]['width'] = idx_wdt

        self.set_row_params()
        self.update_column_align()
        self.update_column_width()
        self.results_row(self.col_lbl)
        
        lines = [ "=" * int(x) for x in self.col_wdt ]
        blank = [ " " * int(x) for x in self.col_wdt ]

        self.results_row(lines)

        keys = list(self.results.keys())
        rows = len(keys)

        for i in range(self.max_rows):
            elem = list(map(self.results[keys[i]].get, self.col_lbl)) if i < rows else blank

            self.results_row(elem)

        self.results_row(lines)
        self.cprint(f'{self.last_msg}')
   
    def load_results(self):
        self.set_status(self.search_msg.format(query = self.query))

        self.results     = self.parser.get_results()
        self.last_page   = self.win_page + 1 if self.win_page + 1 > self.last_page and len(self.parser.results) > self.max_rows * self.win_page else self.last_page
        self.results_len = len(self.parser.results)
        self.input_msg   = f'{self.results_len} results. Pg. {self.win_page}/{self.last_page}: '

    def results_row(self, label):
        _, new_wdt = self.stdscr.getmaxyx()
        zip_col = zip(self.col_wdt, self.col_aln)
        fmt     = " ".join("{:" + aln + str(wdt) + "." + str(wdt) + "}" for wdt, aln in zip_col)
        row     = fmt.format(*label)

        self.cprint(row[:new_wdt])

    def set_row_params(self):
        self.term_hgt = self.stdscr.getmaxyx()[0]
        self.term_wdt = self.stdscr.getmaxyx()[1]
        self.max_rows = self.term_hgt - 5

    def update_column_align(self):
        fxd_wdt = sum(self.cols[col]['width'] for col in self.col_lbl if not self.cols[col]['flex-width'])
        sep_wdt = len(self.col_lbl) - 1
        avl_wdt = self.term_wdt - fxd_wdt - sep_wdt
        num_flx_cols = sum(1 for col in self.col_lbl if self.cols[col]['flex-width'])

        if num_flx_cols > 0:
            flx_col_wdt = max(avl_wdt // num_flx_cols, 1)

            for column in self.col_lbl:
                if self.cols[column]['flex-width']:
                    self.cols[column]['width'] = flx_col_wdt

    def update_column_width(self):
        self.col_wdt = [ col['width'] for col in self.cols.values() ]

    def cprint(self, text, set_space = True, new_line = True):
        text  = text[:self.term_wdt] if len(text) > self.term_wdt else text
        space = " " * (self.term_wdt - len(text)) if set_space else ""
        regex = r'[^\x00-\xff]'
        plhld = '■'
        pfx   = '' if new_line else '\r'
        value = re.sub(regex, plhld, f'{pfx}{text}{space}')
    
        try:
            self.stdscr.addstr(value)     # Print value

        except curses.error:                       # If error is caught...
            pass                                   # ...ignore it

        self.stdscr.refresh()                      # Refresh screen

    def cinput(self, text):
        y, x = self.stdscr.getyx()

        self.stdscr.move(y, 0)
        self.stdscr.deleteln()
        self.stdscr.addstr(f'{text}')
        self.stdscr.keypad(1)
        curses.echo()
        curses.cbreak()

        x_0 = int(x)
        input_str = ''

        while True:
            cur_hgt = self.term_hgt
            cur_wdt = self.term_wdt
            new_hgt, new_wdt = self.stdscr.getmaxyx()

            if cur_hgt != new_hgt or cur_wdt != new_wdt:
                self.show_results()

            self.cprint(f'{text}{input_str}', False, False)

            key  = self.stdscr.getch()
            y, x = self.stdscr.getyx()

            if key in self.key_cmds.keys():
                self.key_cmds[key]()

                break

            elif key in self.back_key:
                if x >= x_0:
                    x -= 1
                    # self.stdscr.move(y, x)
                    self.stdscr.delch()
                    input_str = input_str[:-1]

                else:
                    self.stdscr.move(y, x_0)

            elif key == 10:
                break

            elif 32 <= key <= 126:
                input_str += chr(key)
                x += 1

        curses.noecho()

        return input_str

    def home(self):
        self.turn_page(1)

    def end(self):
        self.turn_page(self.last_page)

    def pgup(self):
        self.turn_page(self.win_page - 1)

    def pgdn(self):
        self.turn_page(self.win_page + 1)

    def turn_page(self, page):
        if 1 <= page <= self.last_page:
            self.win_page = page

            self.set_status(f'Loading page {page}')
            self.show_results()
            self.load_results() 
            self.set_status(self.search_msg.format(query = self.query))
            self.show_results()

    def help(self):
        msg = self.help_msg if self.last_msg != self.help_msg else f'Search results: {self.query}'
        self.set_status(msg)
        self.show_results()

    def set_params(self):
        self.set_status('Setting params in progress')
        self.show_results()

    def quit(self):
        self.set_status('Exiting...')
        self.show_results()
        self.end_prog = True

    def set_status(self, msg):
        self.last_msg = f'{self.ssl_warn}{msg}'

    def set_key_col(self, cols):
        for col in cols.keys():
            if "key" in cols[col].keys():
                return col

    def set_idx_col(self, cols):
        idx = { "idx" : { "align" : ">"
                        , "width" :   2
                        , "flex-width" : False
                        }
              }
        idx_col = "idx"
        cols    = {**idx, **cols}

        return idx_col, cols
