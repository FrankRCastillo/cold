#!/usr/bin/env python3

import argparse
import curses
import json
import os
import sys

from src.cli    import Interface

def main(config, query):
    session = Interface(config, query)

    curses.wrapper(session.start_interface)

if __name__ == '__main__':
    parser = argparse.ArgumentParser( prog = 'cold'
                                    , description = 'COmmand Line Downloader: CLI-based scraping/downloading tool'
                                    )

    parser.add_argument('config', help = 'Configuration')
    parser.add_argument('query' , help = 'Search query')

    ARGS = parser.parse_args()

    root_dir    = os.path.abspath(os.curdir)
    config_dir  = os.path.join(root_dir, 'config')
    config_path = os.path.join(config_dir, ARGS.config)

    if not os.path.isfile(config_path):
        config_list = ", ".join(os.listdir(config_dir))

        print(f'Invalid config name. Available config(s): {config_list}')

        sys.exit()

    with open(config_path) as f:
        config = None

        try:
            config = json.load(f)

        except Exception as e:
            print(f'Error reading config file: {e}')
            sys.exit()

        main(config, ARGS.query)
