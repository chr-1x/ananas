#!/usr/bin/env python3
import os, sys, signal, argparse, configparser, traceback, time
from contextlib import closing
from ananas import PineappleBot
import ananas.default

# Add the cwd to the module search path so that we can load user bot classes
sys.path.append(os.getcwd())

bots = []

def shutdown_all(signum, frame):
    for bot in bots:
        if bot.state == PineappleBot.RUNNING: bot.shutdown()
    sys.exit("Shutdown complete")

def main():
    parser = argparse.ArgumentParser(description="Pineapple command line interface.", prog="ananas")
    parser.add_argument("config", help="A cfg file to read bot configuration from.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Log more extensive messages for e.g. debugging purposes.")
    parser.add_argument("-i", "--interactive", action="store_true", help="Use interactive prompts for e.g. mastodon login")
    args = parser.parse_args()

    prog = sys.argv[0]

    cfg = configparser.ConfigParser()
    try: cfg.read(args.config)
    except FileNotFoundError:
        sys.exit("Couldn't open '{}', exiting.".format(args.config))

    for bot in cfg:
        if bot == "DEFAULT": continue
        if not "class" in cfg[bot]:
            print("{}: no class specified, skipping {}.".format(prog, bot))
            continue

        botclass = cfg[bot]["class"]
        module, _, botclass = botclass.rpartition(".")
        if module == "":
            print("{}: no module given in class name '{}', skipping {}.".format(prog, botclass, bot))

        try:
            exec("from {0} import {1}; bots.append({1}('{2}', name='{3}', interactive={4}, verbose={5}))"
                    .format(module, botclass, args.config, bot, args.interactive, args.verbose))
        except ModuleNotFoundError as e:
            print("{}: couldn't load module {}, skipping {}.".format(prog, module, bot))
            continue
        except Exception as e:
            print("{}: fatal exception loading bot {}: {}\n{}".format(prog, bot, repr(e), traceback.format_exc()))
            continue
        except KeyboardInterrupt:
            sys.exit()

    signal.signal(signal.SIGINT, shutdown_all)
    signal.signal(signal.SIGABRT, shutdown_all)
    signal.signal(signal.SIGTERM, shutdown_all)

    try:
        while(True): time.sleep(60)
    except KeyboardInterrupt:
        shutdown_all(None, None)

if __name__ == "__main__":
    main()
