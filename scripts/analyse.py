"""Saved numeric analysis only; invoke with PYTHONPATH=src from the checkout."""
from ws_lab.reproduce import main

if __name__ == '__main__':
    import sys
    raise SystemExit(main(['analyse', *sys.argv[1:]]))
