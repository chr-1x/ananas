Ananas
======

What is Ananas?
---------------

Ananas allows you to write simple (or complicated!) mastodon bots without having
to rewrite config file loading, interval-based posting, scheduled posting,
auto-replying, and so on.

Some bots are as simple as a configuration file:

::

    [bepis]
    class = tracery.TraceryBot
    access_token = ....
    grammar_file = "bepis.json"

But it's easy to write one with customized behavior:

::

    class MyBot(ananas.PineappleBot):
        def start(self):
            with open('trivia.txt', 'r') as trivia_file:
               self.trivia = trivia_file.lines()

        @hourly(minute=17)
        def post_trivia(self):
            self.mastodon.toot(random.choice(self.trivia))

        @reply
        def respond_trivia(self, status, user):
            self.mastodon.toot("@{}: {}".format(user["acct"], random.choice(self.trivia)))

Run multiple bots on multiple instances out of a single config file:

::

    [jorts]
    class = custom.JortsBot
    domain = botsin.space
    access_token = ....
    line = 632

    [roll]
    class = roll.DiceBot
    domain = cybre.space
    access_token = ....

And use the DEFAULT section to share common configuration options between them:

::

    [DEFAULT]
    domain = cybre.space
    client_id = ....
    client_secret = ....

Getting started
---------------

::

    pip install ananas

The ``ananas`` pip package comes with a script to help you manage your bots.

Simply give it a config file and it'll load your bots and close them safely
when it receives a keyboard interrupt, SIGINT, SIGTERM, or SIGKILL.

::

    ananas config.cfg

If you haven't specified a client id/secret or access token, the script will
exit unless you run it with the ``--interactive`` flag, which allows it to
prompt you for the instance login information. (The only part of the input
you enter here that's stored in the config file is the instance name -- the
email and password are only used to generate the access token).

Configuration
-------------

The following fields are interpreted by the PineappleBot base classs and will
work for every bot:

**class**: the fully-specified python class that the runner script should
instantiate to start your bot. e.g. "ananas.default.TraceryBot"

**domain**\ ¹: the domain of the instance to run the bot on. Must support https
connections. Only include the domain, no protocol or slashes. e.g.  "mastodon.social"

**client\_id**\ ¹, **client\_secret**\ ¹: the tokens that the instance uses to identify
what client this bot is posting from/as. Will be used to determine what's
displayed underneath all the posts made by this bot.

**access\_token**\ ¹: the access token used to authenticate API requests with the
instance. Make sure this is secret, don't distribute config files with this
field filled out or people will be able to post under the account this token was
created with.

**admin**: the full username (without leading @) of the user to DM error reports to.
Can be left unspecified, but is useful for keeping an eye on the health of the
bot without constantly monitoring the script logs. e.g.  ``admin@example.town``

¹: Filled out automatically if the bot is run in interactive mode.

Additional fields are specific to the type of bot, refer to the documentation
for the bot's class for more information about the fields it expects.

Writing Bots
------------

Custom bot classes should be subclasses of ``ananas.PineappleBot``. If you
override ``__init__``, be sure to call the base class's ``__init__``.

Decorators
~~~~~~~~~~

In order for the bot to do anything, you should add a method decorated with at
least one of the following decorators:

**@ananas.reply**: Calls the decorated function when the bot is mentioned by any
other user. Decorator takes no parameters, but should only be called on
functions matching this signature: ``def reply_fn(self, mention, user)``.
``mention`` will be the dictionary corresponding to the status containing the
mention (as returned by the `mastodon API <https://github.com/tootsuite/documentation/blob/master/Using-the-API/API.md>`__),
``user`` will be the dictionary corresponding to the user that mentioned the bot.

**@ananas.interval\ (secs)**: Calls the decorated function every ``secs`` seconds,
starting when the bot is initialized. For intervals longer than ~an hour, you
may want to use ``@schedule`` instead. e.g. ``@ananas.interval(60)``

**@ananas.schedule\ (\*\*kwargs)**: Allows you to schedule, cron-style, the
decorated function. Accepted keywords are "second", "minute", "hour",
"day\_of\_week" or "day\_of\_month" (but not both), "month", and "year". If any of
these keywords are not specified, they will be treated like cron treats an \*,
that is, as long as the time matches the other values, any value will be
accepted. See the docs for more information.

**@ananas.hourly\ (minute=0)**, **\ @ananas.daily(hour=0, minute=0)**: Shortcuts for
``@ananas.schedule()`` that call the decorated function once an hour at the
specified minute or once a day at the specified hour and minute. If parameters
are omitted they'll post at the top of the hour or midnight (UTC).

**@ananas.error_reporter**: specifies custom behavior for reporting errors. The
decorated function should match this signature: ``def err(self, error)`` where
``error`` is a string representation of the error.

Overrideable Functions
~~~~~~~~~~~~~~~~~~~~~~

You can also define the following functions and they will be called at the
relevant points in the bot's lifecycle:

**init(self)**: called before the configuration file has been loaded, so
that you can set default values for config fields in case the config file
doesn't specify them.

**start(self)**: called after all of the internal PineappleBot initialization is
complete and the mastodon API is ready to use. A good place to load files
specified in the config, post a startup notice, or otherwise do bot-specific
setup.

**stop(self)**: called when the bot has received a shutdown signal and needs to
stop. The config file will be saved after this, so if you need to make any last
minute changes to the config, do that here.

Configuration Fields
~~~~~~~~~~~~~~~~~~~~

All of the configuration fields for the current bot are available through the
``self.config`` object, which exposes them with both field-accessor syntax and
dictionary-accessor syntax, for example:

::

    foo = self.config.foo
    bar = self.config["bar"]

These can be read (to get the user's configuration data) or written to (to
affect the config file on next save) or deleted (to remove that field from the
config file).

You can call ``self.config.load()`` to get the latest values from the config
file. ``load`` takes an optional parameter ``name``, which is the name of the
section to load in the config file in case you want to load a different one than
the bot was started with.

You can also call ``self.config.save()`` to write any changes made since the last
load back to the config file.

Note that if you call ``self.config.load()`` during bot operation, without first
calling ``self.config.save()``, you will discard any changes made to the
configuration since the last load.

Distributing Bots
-----------------

You can distribute bots however you want; as long as the class is available in
some module in python's ``sys.path`` or a module accessible from the current
directory, the runner script will be able to load it.

If you think your bot might be generally useful to other people, feel free to
create a pull request on this repository to get it added to the collection of
default bots.

Distributing Bots
-----------------

Questions? Ping me on Mastodon at @chr@cybre.space or shoot me an email at
chr@cybre.space and I'll answer as best I can!
