#!/usr/bin/env python3

import argparse
import curses
import json
import sys
from importlib import resources
from pathlib import Path

from .cli import Interface

def main():
    config_obj = None
    try:
        config_dir = resources.files("cold").joinpath('config')
    except Exception:
        config_dir = Path(__file__).resolve().parent / "config"

    try:
        config_names = sorted([p.name for p in config_dir.iterdir() if p.is_file()])
    except Exception:
        config_names = []

    config_list = ", ".join(config_names) if config_names else "(none found)"

    parser = argparse.ArgumentParser( prog = 'cold'
                                    , description = 'COmmand Line Downloader: CLI-based scraping/downloading tool'
                                    )

    parser.add_argument('config', type = str, help = f'Configuration file. Available config(s): {config_list}')
    parser.add_argument('query' , type = str, help = 'Search query')

    parser_args = parser.parse_args()
    config_val  = parser_args.config
    query_val   = parser_args.query
    config_path = config_dir.joinpath(config_val)
    if not config_path.is_file():
        print(f'Invalid config name. Available config(s): {config_list}')
        sys.exit()

    try:
        with config_path.open('r', encoding='utf-8') as f:
            config_obj = json.load(f)
    except Exception as e:
        print(f'Error reading config file: {e}')
        sys.exit()

    session = Interface(config_obj, query_val)

    try:
        curses.wrapper(session.start_interface)
    except curses.error:
        try:
            curses.endwin()
        except curses.error:
            pass

if __name__ == '__main__':
    main()
