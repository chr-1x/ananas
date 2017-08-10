#!/usr/bin/env python3
import sys, signal

from jort import jorts
from psa import psa
from roll import roll
from proboscidean import Proboscidean

bots = []

def shutdown_all(signum, frame):
    for bot in bots:
        if bot._state == Proboscidean.RUNNING: bot.shutdown()

if __name__ == "__main__":
    #signal.signal(signal.SIGINT, shutdown_all)
    #signal.signal(signal.SIGABRT, shutdown_all)
    #signal.signal(signal.SIGTERM, shutdown_all)
    bots = [jorts(interactive=True), psa(interactive=True), roll(interactive=True)]
    try:
        while(True): pass
    except KeyboardInterrupt:
        shutdown_all(None, None)
        print("Shut down completely.")
