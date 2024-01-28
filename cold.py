#!/usr/bin/env python3

import argparse
import curses
import json
import os
import sys

from src.cli import Interface

def main():
    parser = argparse.ArgumentParser( prog = 'cold'
                                    , description = 'COmmand Line Downloader: CLI-based scraping/downloading tool'
                                    )

    parser.add_argument('config', type = str, help = 'Configuration')
    parser.add_argument('query' , type = str, help = 'Search query')

    parser_args = parser.parse_args()
    config_val  = parser_args.config
    query_val   = parser_args.query
    script_dir  = os.path.dirname(os.path.realpath(__file__))
    config_dir  = os.path.join(script_dir, 'config')
    config_path = os.path.join(config_dir, config_val)
    config_obj  = None

    if not os.path.isfile(config_path):
        config_list = ", ".join(os.listdir(config_dir))

        print(f'Invalid config name. Available config(s): {config_list}')

        sys.exit()

    with open(config_path) as f:
        try:
            config_obj = json.load(f)

        except Exception as e:
            print(f'Error reading config file: {e}')
            sys.exit()

    session = Interface(config_obj, query_val)

    curses.wrapper(session.start_interface)

if __name__ == '__main__':
    main()
