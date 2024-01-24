import curses
import math
import re

from src.dl     import Downloader
from src.parser import Parse_Results

class Interface:
    def __init__(self, config, query):
        self.config     = config
        self.url        = config['url']
        self.params     = config['params']
        self.id_col, self.cols = self.set_id_col(config['columns'])
        self.link_xpath = config['link']
        self.download   = config['download']
        self.ssl_verify = config['ssl-verify']
        self.query      = query
        self.results    = {}
        self.end_prog   = False
        self.col_lbl    = list(self.cols.keys())
        self.col_aln    = [ col['align'] for col in self.cols.values() ]
        self.col_wdt    = [ col['width'] for col in self.cols.values() ]
        self.back_key   = [ curses.KEY_BACKSPACE, 127, 8, 263 ]
        self.key_cmds   = { curses.KEY_HOME  : self.home
                          , curses.KEY_PPAGE : self.pgup
                          , curses.KEY_NPAGE : self.pgdn
                          , curses.KEY_F1    : self.sort
                          , curses.KEY_F2    : self.fltr
                          , 27               : self.quit
                          }

        self.menu_arr   = [ f'{self.id_col}<Enter> Download'
                          , 'query<Enter> Search'
                          , '<home> First'
                          , '<pgup> Prev'
                          , '<pgdn> Next'
                          , '<F1> Sort'
                          , '<F2> Filter'
                          , '<Esc> Quit'
                          ]
        self.menu_str   = ", ".join(self.menu_arr)

    def start_interface(self, stdscr):
        self.stdscr = stdscr

        self.set_row_params()

        self.ssl_warn = 'WARNING: SSL VERIFICATION IS DISABLED! ' if not self.ssl_verify else ''
        self.last_msg = f'Search results: {self.query}'
        self.dl       = Downloader(self)
        self.parser   = Parse_Results(self, self.dl)

        self.update_column_align()
        self.update_column_width()
        curses.start_color()

        while not self.end_prog:
            self.parser.get_results(self.query) 
            self.results_len = len(self.results.keys())
            self.page_num    = self.parser.win_page
            self.input_msg   = f'\r{self.ssl_warn}{self.results_len} results. Pg. {self.page_num} ({self.menu_str}): '

            self.show_results()

            user_input = self.cinput(self.input_msg)
            
            if self.end_prog:
                break

            if user_input in self.results.keys():
                self.last_msg = f'Downloading {user_input}'

                url = self.results[user_input].get('link')

                if not url:
                    link_row = self.results[user_input]['link_row']
                    self.last_msg = f'Resolving link for {user_input}...'
                    self.results[user_input]['link'] = self.parser.get_link(link_row, self.link_xpath)
                    url = self.results[user_input]['link']

                self.dl.get_file(url)

            elif user_input != "":
                self.query    = user_input
                self.last_msg = f'Search results: {self.query}'

        curses.echo()
        curses.endwin()

    def show_results(self):
        self.stdscr.clear()
        self.set_row_params()

        rslt_max = int(list(self.results.keys())[-1])
        idx_wdt = int(math.log(rslt_max, 10) + 2)
        self.cols[self.id_col]['width'] = idx_wdt

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
    
    def results_row(self, label):
        self.update_column_align()
        self.update_column_width()

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
        # Calculate the total width of fixed columns and separators
        fxd_wdt = sum(self.cols[col]['width'] for col in self.col_lbl if not self.cols[col]['flex-width'])
        sep_wdt = len(self.col_lbl) - 1  # Assuming 1 unit per separator
        avl_wdt = self.term_wdt - fxd_wdt - sep_wdt
        num_flx_cols = sum(1 for col in self.col_lbl if self.cols[col]['flex-width'])

        # Distribute the available width among flexible columns
        if num_flx_cols > 0:
            flx_col_wdt = max(avl_wdt // num_flx_cols, 1)  # Ensure it's not negative
            for column in self.col_lbl:
                if self.cols[column]['flex-width']:
                    self.cols[column]['width'] = flx_col_wdt

    def update_column_width(self):
        self.col_wdt = [ col['width'] for col in self.cols.values() ]

    def cprint(self, text, set_space = True):
        text  = text[:self.term_wdt] if len(text) > self.term_wdt else text
        space = " " * (self.term_wdt - len(text)) if set_space else ""
        regex = r'[^\x00-\xff]'
        plhld = '■'
        value = re.sub(regex, plhld, f'{text}{space}')
    
        try:
            (y, x) = self.stdscr.getyx()    # Get the current position of the cursor
            y = y + 1 if x > 0 else y       # Move to the next line if not at the start
            self.stdscr.move(y, 0)          # Move cursor to the start of the next line
            self.stdscr.clrtoeol()          # Clear the rest of the line
            self.stdscr.addstr(value)       # Print value

        except curses.error:                # If error is caught...
            pass                            # ...ignore it

        self.stdscr.refresh()               # Refresh screen

    def cinput(self, text):
        y, x = self.stdscr.getyx()

        self.stdscr.move(y, 0)
        self.stdscr.deleteln()
        self.stdscr.addstr(f'{text}')
        self.stdscr.keypad(1)
        curses.echo()
        curses.cbreak()

        x_0  = int(x)
        input_str = ''

        while True:
            cur_hgt = self.term_hgt
            cur_wdt = self.term_wdt
            new_hgt, new_wdt = self.stdscr.getmaxyx()

            if cur_hgt != new_hgt or cur_wdt != new_wdt:
                self.show_results()


            self.cprint(f'\r{text}{input_str}', False)
            # self.stdscr.addstr(f'{text}{input_str}')

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
        page = 1
        self.turn_page(page)

    def pgup(self):
        page = self.parser.win_page
        page = 1 if page == 1 else page - 1
        self.turn_page(page)

    def pgdn(self):
        page = self.parser.win_page + 1
        self.turn_page(page)

    def turn_page(self, page):
        self.parser.win_page = page
        self.parser.get_results(self.query)
        self.show_results()
        self.last_msg = f'Changed page to # {page}'

    def sort(self):
        self.last_msg = 'Sorting...'

    def fltr(self):
        self.last_msg = 'Filtering...'

    def quit(self):
        self.last_msg = 'Exiting...'
        self.end_prog = True

    def set_id_col(self, cols):
        id_col = None

        for col in cols.keys():
            if "id-column" in cols[col].keys():
                id_col = col

        if id_col is None:
            idx = { "idx" : { "align" : ">"
                            , "width" :   2
                            , "flex-width" : False
                            }
                  }
            id_col = "idx"
            cols   = {**idx, **cols}

        return id_col, cols
