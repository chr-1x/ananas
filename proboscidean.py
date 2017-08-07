import os, sys, time, datetime, threading, configparser, inspect
from mastodon import Mastodon

def interval(seconds):
    def wrapper(f):
        f.interval = seconds
        return f
    return wrapper

def reply(f):
    f.reply = True
    return f

class Proboscidean:
    INITIALIZING = 0
    STARTING = 1
    RUNNING = 2
    STOPPING = 3

    CONFIG = "config.cfg"

    def __init__(self, name=None, log_to_stderr=True, use_common_cfg=True):
        if (name is None): name = self.__class__.__name__
        self.name = name
        self._state = Proboscidean.INITIALIZING

        self._alive = threading.Condition()
        self._threads = []
        self._reply_funcs = []

        self.username = ""
        self.display_name = ""
        self._mastodon = None

        self._log_to_stderr = log_to_stderr
        self._logname = self.name + ".log"
        self._log = open(self._logname, "a")

        self._use_common_cfg = use_common_cfg
        self._cfgname = Proboscidean.CONFIG if self._use_common_cfg else self.name + '.cfg'

        self.init()
        self.load_from_cfg()

        self.startup()

    def load_from_cfg(self):
        cfg = configparser.ConfigParser()
        cfg.read(self._cfgname)

        if (self.name not in cfg.sections()):
            self.log(None, "\"{0}\" section not found in {1}, aborting.\n".format(self.name, self._cfgname))

        section = cfg[self.name]
        for attr in section:
            setattr(self, attr, section[attr])

    def save_to_cfg(self):
        cfg = configparser.ConfigParser()
        cfg.read(self._cfgname)

        if (self.name not in cfg.sections()):
            self.log(None, "\"{0}\" section not found in {1}, aborting.\n".format(self.name, self._cfgname))

        section = cfg[self.name]
        for attr, value in self.__dict__.items():
            if attr[0] != '_':
                cfg[attr] = value
        with open(self._cfgname, 'w') as cfgfile:
            cfg.write(cfgfile)

    def startup(self):
        self._state = Proboscidean.STARTING
        self.log(None, "Starting bot of type {0}".format(self.name))

        self.start()
        
        def interval_threadproc(f):
            self.log(f.__name__, "Running with interval {0}".format(f.interval))
            while (True):
                self._alive.acquire()
                f()
                self._alive.wait(f.interval)
                if (self._state == Proboscidean.STOPPING):
                    self._alive.release()
                    self.log(f.__name__, "Shutting down")
                    return 0
                else:
                    self._alive.release()

        for fname, f in inspect.getmembers(self, predicate=inspect.ismethod):
            if hasattr(f, "interval"):
                t = threading.Thread(args=(f,), target=interval_threadproc)
                t.start()
                self._threads.append(t)

            if hasattr(f, "reply"):
                self._reply_funcs.append(f)

        self._state = Proboscidean.RUNNING

    @interval(seconds=60)
    def run_scheduled(self):
        pass

    @interval(seconds=30)
    def check_mentions(self):
        pass

    def shutdown(self):
        self._alive.acquire()
        self._state = Proboscidean.STOPPING
        self.log(None, "Stopping bot of type {0}".format(self.name))
        self._alive.notify_all()
        self._alive.release()

        self._log.close()

    def log(self, id, msg):
        if (id == None): id = self.name
        else: id = self.name + "." + id
        ts = datetime.datetime.now()
        msg_f = "[{0:%Y-%m-%d %H:%M:%S}] {1}: {2}".format(ts, id, msg)

        if self._log.closed or self._log_to_stderr: print(msg_f, file=sys.stderr)
        if not self._log.closed: print(msg_f, file=self._log)

    def toot(self):
        pass

