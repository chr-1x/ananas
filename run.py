#!/usr/bin/env python3
import sys, signal

from jort import jorts
from psa import psa
from roll import roll
from pineapple import PineappleBot

bots = []

def shutdown_all(signum, frame):
    for bot in bots:
        if bot._state == PineappleBot.RUNNING: bot.shutdown()

if __name__ == "__main__":
    #signal.signal(signal.SIGINT, shutdown_all)
    #signal.signal(signal.SIGABRT, shutdown_all)
    #signal.signal(signal.SIGTERM, shutdown_all)
    bots = [psa(interactive=True), jorts(interactive=True), roll(interactive=True)]
    try:
        while(True): pass
    except KeyboardInterrupt:
        shutdown_all(None, None)
        print("Shut down completely.")
