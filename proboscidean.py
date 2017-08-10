import os, sys, re, time, datetime, threading, configparser, inspect, getpass
import mastodon
from mastodon import Mastodon

def interval(seconds):
    def wrapper(f):
        f.interval = seconds
        return f
    return wrapper

def reply(f):
    f.reply = True
    return f

def scheduled(**kwargs):
    def wrapper(f):
        f.scheduled = kwargs
        return f
    return wrapper

class Proboscidean:
    INITIALIZING = 0
    STARTING = 1
    RUNNING = 2
    STOPPING = 3

    CONFIG = "config.cfg"

    _http_re = re.compile("^http[s]?://.*$")

    def __init__(self, name=None, log_to_stderr=True, use_common_cfg=True, interactive=False):
        if (name is None): name = self.__class__.__name__
        self.name = name
        self._state = Proboscidean.INITIALIZING

        self._alive = threading.Condition()
        self._threads = []
        self._reply_funcs = []

        self._mastodon = None
        self._interactive = interactive

        self._log_to_stderr = log_to_stderr
        self._logname = self.name + ".log"
        self._log = open(self._logname, "a")

        self._use_common_cfg = use_common_cfg
        self._cfgname = Proboscidean.CONFIG if self._use_common_cfg else self.name + '.cfg'

        self.init() # Call user init to initialize bot-specific properties to default values
        if not self.load_from_cfg(): return
        if not self.login(): return

        self.startup()

    def load_from_cfg(self):
        cfg = configparser.ConfigParser()
        cfg.read(self._cfgname)

        if (self.name not in cfg.sections()):
            self.log(None, "\"{0}\" section not found in {1}, aborting.".format(self.name, self._cfgname))
            return False

        section = cfg[self.name]
        for attr in section:
            setattr(self, attr, section[attr])
        return True

    def save_to_cfg(self):
        cfg = configparser.ConfigParser()
        cfg.read(self._cfgname)

        if (self.name not in cfg.sections()):
            self.log("save_to_cfg", "\"{0}\" section not found in {1}, aborting.".format(self.name, self._cfgname))
            return False

        section = cfg[self.name]
        for attr, value in self.__dict__.items():
            if attr[0] != '_' and attr != "name":
                section[attr] = str(value)
        self.log("save_to_cfg", "Saving configuration to file...")
        with open(self._cfgname, 'w') as cfgfile:
            cfg.write(cfgfile)
        self.log("save_to_cfg", "Done")
        return True

    # defaults, should be replaced by concrete bots with actual implementations
    # (if necessary, anyway)
    def init(self):
        pass
    def start(self):
        pass
    def stop(self):
        pass

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

        self.stop()
        self.save_to_cfg()

        self._log.close()

    def log(self, id, msg):
        if (id == None): id = self.name
        else: id = self.name + "." + id
        ts = datetime.datetime.now()
        msg_f = "[{0:%Y-%m-%d %H:%M:%S}] {1}: {2}".format(ts, id, msg)

        if self._log.closed or self._log_to_stderr: print(msg_f, file=sys.stderr)
        if not self._log.closed: print(msg_f, file=self._log)

    def login(self):
        if self._interactive and not self.interactive_login(): 
            self.log("api", "Interactive login failed, exiting.")
            return False
        elif (not hasattr(self, "domain")):
            self.log("api", "No domain set in config and interactive = False, exiting.")
            return False
        elif (not hasattr(self, "client_id")):
            self.log("api", "No client id set in config and interactive = False, exiting.")
            return False
        elif (not hasattr(self, "client_secret")):
            self.log("api", "No client secret set in config and interactive = False, exiting.")
            return False
        elif (not hasattr(self, "access_token")):
            self.log("api", "No access key set in config and interactive = False, exiting.")
            return False

        self._mastodon = Mastodon(client_id = self.client_id, 
                                  client_secrect = self.client_secret, 
                                  access_token = self.access_token, 
                                  api_base_url = self.domain)
        return True

    def interactive_login(self):
        if (not hasattr(self, "domain")):
            domain = input("{0}: Enter the instance domain [mastodon.social]: ".format(self.name))
            domain = domain.strip()
            if (domain == ""): domain = "mastodon.social"
            self.domain = domain
        # We have to generate these two together, if just one is 
        # specified in the config file it's no good.
        if (not hasattr(self, "client_id") or not hasattr(self, "client_secret")):
            client_name = input("{0}: Enter a name for this bot or service [{0}]: ".format(self.name))
            client_name = client_name.strip()
            if (client_name == ""): client_name = self.name
            self.client_id, self.client_secret = Mastodon.create_app(client_name, 
                                                                     "https://"+self.domain)
            # TODO handle failure
            self.save_to_cfg()
        if (not hasattr(self, "access_token")):
            email = input("{0}: Enter the account email: ".format(self.name))
            email = email.strip()
            password = getpass.getpass("{0}: Enter the account password: ".format(self.name))
            try:
                mastodon = Mastodon(client_id = self.client_id,
                                    client_secret = self.client_secret,
                                    api_base_url = "https://"+self.domain)
                self.access_token = mastodon.log_in(email, password)
            except ValueError as e:
                self.log("login", "Could not authenticate with {0} as '{1}'".format(self.domain, email))
                self.log("debug", "using the password {0}".format(password))
                return False
        return True

    def toot(self, msg):
        self._mastodon.toot(msg)
