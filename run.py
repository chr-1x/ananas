#!/usr/bin/env python3
import sys, signal

from jort import jorts
from psa import psa
from roll import DiceBot
from tracery import TraceryBot
from pineapple import PineappleBot

bots = []

def shutdown_all(signum, frame):
    for bot in bots:
        if bot._state == PineappleBot.RUNNING: bot.shutdown()
    sys.exit("Shutdown complete")

if __name__ == "__main__":
    signal.signal(signal.SIGINT, shutdown_all)
    signal.signal(signal.SIGABRT, shutdown_all)
    signal.signal(signal.SIGTERM, shutdown_all)
    #bots = [psa(interactive=True), jorts(interactive=True),
            #DiceBot(interactive=True), TraceryBot(interactive=True, name="bepis")]
    bots = [DiceBot(interactive=True, name="roll")]
    try:
        while(True): pass
    except KeyboardInterrupt:
        shutdown_all(None, None)
