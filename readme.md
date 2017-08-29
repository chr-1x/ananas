# Ananas
The Python Bot Framework for Mastodon

## What is Ananas?

Ananas allows you to write simple (or complicated!) mastodon bots without having
to recreate config file loading, interval-based posting, scheduled posting,
auto-replying, and so on.

Some bots are as simple as a configuration file:

    [bepis]
    class = tracery.TraceryBot
    access_token = ....
    grammar_file = "bepis.json"

But it's easy to write one with customized behavior:

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

    [DEFAULT]
    domain = cybre.space
    client_id = ....
    client_secret = ....

# Getting started
[Pypi instructions coming soon!]

Clone this repository somewhere:

    git clone https://github.com/Chronister/ananas.git

