import os, sys, re, time, threading
import calendar
from datetime import datetime, timedelta, timezone
import configparser, inspect, getpass, traceback
from html.parser import HTMLParser
import mastodon
from mastodon import Mastodon, StreamListener

# Decorators

def reply(f):
    f.reply = True
    return f

def interval(seconds):
    def wrapper(f):
        f.interval = seconds
        return f
    return wrapper

def scheduled(**kwargs):
    def wrapper(f):
        if (not hasattr(f, "scheduled")):
            f.scheduled = [kwargs]
        else:
            f.scheduled.append(kwargs)
        return f
    return wrapper

# Utilities

def total_seconds(dt):
    """Returns the total number of seconds in a timedelta."""
    return dt.seconds + dt.days * 24 * 60 * 60

def schedule_next(f, t = datetime.now(), tLast = datetime.now()):
    """
    Calculate the number of seconds from now until the function should next run.
    This function handles both cron-like and interval-like scheduling via the
    following:
     ∗ If no interval and no schedule are specified, return 0
     ∗ If an interval is specified but no schedule, return the number of seconds
       from <t> until <interval> has passed since <tLast> or 0 if it's overdue.
     ∗ If a schedule is passed but no interval, figure out when next to run by
       parsing the schedule according to the following rules:
         ∗ If all of second, minute, hour, day_of_week/day_of_month, month, year
           are specified, then the time to run is singular and the function will
           run only once at that time. If it has not happened yet, return the
           number of seconds from <t> until that time, otherwise return -1.
         ∗ If one or more are unspecified, then they are treated as open slots.
           return the number of seconds from <t> until the time next fits within
           the specified constraints, or if it never will again return -1.
             ∗ Only one of day_of_week and day_of_month may be specified. if both
               are specified, then day_of_month is used and day_of_week is ignored.
         ∗ If all are unspecified treat it as having no schedule specified
     ∗ If both a schedule and an interval are specified, TODO but it should do
       something along the lines of finding the next multiple of interval from tLast 
       that fits the schedule spec and returning the number of seconds until then.
    """
    has_interval = hasattr(f, "interval")
    has_schedule = hasattr(f, "schedule")
    schedule_fields = ["second", "minute", "hour", "day_of_week", "day_of_month", "month", "year"]
    has_schedule = has_schedule and any(k in f.schedule for k in schedule_fields))
    if (not has_interval and not has_schedule):
        return 0
    if (has_interval and not has_schedule):
        tNext = tLast + timedelta(seconds = f.interval)
        return max(total_seconds(tNext - t), 0)
    if (has_schedule): # and not has_interval):
        # Operate in day-of-month mode unless day-of-week is specified
        use_day_of_week = "day_of_week" in f.schedule

        SECOND = 0
        MINUTE = 1
        HOUR = 2
        DAY_OF_WEEK = 3
        DAY_OF_MONTH = 3
        MONTH = 4
        YEAR = 5

        MONTH_LIMIT = -2

        spec = []
        now = [t.second, t.minute, t.hour, t.weekday() if use_day_of_week else t.day, t.month, t.year]
        next = [-1, -1, -1, -1, -1, -1]
        wrap = [60, 60, 24, 7 if use_day_of_week else MONTH_LIMIT, 12, 17776]

        def compare(tlist1, tlist2):
            for i in reversed(range(6)):
                if tlist1[i] < tlist2[i]: return -1
                if tlist1[i] > tlist2[i]: return 1
            return 0
        def specified(slot): return spec[slot] != -1

        spec.append(f.schedule.get("second", -1))
        spec.append(f.schedule.get("minute", -1))
        spec.append(f.schedule.get("hour", -1))
        if use_day_of_week:
            spec.append(f.schedule.get("day_of_week", -1))
        else:
            spec.append(f.schedule.get("day_of_month", -1))
        spec.append(f.schedule.get("month", -1))
        spec.append(f.schedule.get("year", -1))

        # the largest slot such that the value for now in that slot was actually
        # greater than a specified value
        largest_spec_clobbered = -1

        for slot, value in spec:
            if value == -1:
                next[slot] = now[slot]
            else:
                next[slot] = spec[slot]
                if now[slot] > spec[slot]:
                    largest_spec_clobbered = slot

        if compare(next, now) < 0:
            # if next is in the past from now, one of the values of now has to
            # have been greater than a specified value
            assert largest_spec_clobbered != -1
            # If the year is specified, there's nothing we can do
            if largest_spec_clobbered == YEAR: return -1

            # find the next largest unspecified slot
            slot_to_incr = largest_slot_clobbered + 1
            while not specified(slot_to_incr): slot_to_incr += 1

            # increment that next largest unspecified slot
            next[slot_to_incr] += 1

        # Now go through and keep the values in range by doing the carry if necessary,
        # and minimize smaller slots to achieve an overall minimal future result.
        # By carrying over specified values, we properly handle the edge cases.
        carry = 0
        for slot in range(6):
            if slot < largest_slot_clobbered:
                if not specified(slot):
                    next[slot] = 0
            else:
                if not specified(slot):
                    lim = wrap[slot]
                    if lim == MONTH_LIMIT:
                        lim = calendar.monthrange(next[YEAR], next[MONTH])[1]
                    carry, next[slot] = divmod(next[slot] + carry, lim)
        assert compare(next, now) > 0

class HTMLTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = ""
    def handle_data(self, data):
        self.text += data;

# TODO: add a parameter for whether to infer linebreaks from the html tags
def html_strip_tags(html_str):
    parser = HTMLTextParser()
    parser.feed(html_str)
    return parser.text


class Proboscidean(StreamListener):
    """
    Main bot class
    We subclass StreamListener so that we can use it as its own callback
    """

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
        # TODO replace with something more intelligent?
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

    def log(self, id, msg):
        if (id == None): id = self.name
        else: id = self.name + "." + id
        ts = datetime.now()
        msg_f = "[{0:%Y-%m-%d %H:%M:%S}] {1}: {2}".format(ts, id, msg)

        if self._log.closed or self._log_to_stderr: print(msg_f, file=sys.stderr)
        if not self._log.closed: print(msg_f, file=self._log)

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
            self.log(f.__name__, "Started")
            while (True):
                self._alive.acquire()
                try:
                    f()
                except Exception as e:
                    self.log(f.__name__, "Fatal exception: {}\n{}".format(repr(e), traceback.format_exc()))
                    self._alive.release()
                    return 0

                interval = schedule_next(f)
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

        self._mastodon.user_stream(self)

        self._state = Proboscidean.RUNNING

    def shutdown(self):
        self._alive.acquire()
        self._state = Proboscidean.STOPPING
        self.log(None, "Stopping bot of type {0}".format(self.name))
        self._alive.notify_all()
        self._alive.release()

        self.stop()
        self.save_to_cfg()

        self._log.close()

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
                                  client_secret = self.client_secret, 
                                  access_token = self.access_token, 
                                  api_base_url = self.domain)
                                  #debug_requests = True)
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
                                                                     api_base_url="https://"+self.domain)
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
                self.log("login", "Could not authenticate with {0} as '{1}': ".format(self.domain, email))
                self.log("login", str(e))
                self.log("debug", "using the password {0}".format(password))
                return False
        self.save_to_cfg()
        return True

    @interval(seconds=60)
    def run_scheduled(self):
        pass

    def on_notification(self, notif):
        self.log("debug", "Got a {} from {} at {}".format(notif["type"], notif["account"]["username"], notif["created_at"]))
        if (notif["type"] == "mention"):
            for f in self._reply_funcs:
                f(notif["status"], notif["account"])

