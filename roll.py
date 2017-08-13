import random, string, itertools
from pineapple import PineappleBot, reply, html_strip_tags

class roll(PineappleBot):

    def start(self):
        pass

    @reply
    def handle_roll(self, mention, user):
        raw = html_strip_tags(mention["content"]) 
        username = user["username"]

        # TODO TEST TEST TEST
        if (username != 'chr'): return

        self.log("handle_roll", "Parsing dice in '{}' from @{}" .format(raw, username))
        rolls = parse_dice()
        message = ""
        for i, r in enumerate(rolls):
            if (len(rolls) > 1):
                message += "Roll {}:".format(i)
            dice = self.roll(dice=r[0], sides=r[1])
            for d in dice:
                message += " [{}]".format(d)
            message += ""

        self._mastodon.status_post("@{}\n{}".format(username, message),
                in_reply_to_id = mention["id"],
                visibility = "direct") #mention["visibility"])

    def parse_dice(text):
        # Formats we accept:
        #  @roll [#]d#[±#]
        #  @roll #d#d#[ٍٍ±#]
        #  @roll #d#k#[ٍٍ±#]
        # We also want to accept any amount of whitespace (but not other
        # characters) between portions of the roll:
        #  @roll 3 d20 + 2
        #  @roll 3d20 k 4 - 2

        # We'll accept multiple rolls, but only up to e.g. 5:
        #  @roll 2d20 2d6

        # Finally, we'll accept simple arithmetic expressions of rolls:
        #  @roll 2d20 + 2d6 

        def tokenizer():
            s = ""
            for c in text:
                if c in string.digits: s += c
                else:
                    if len(s) > 0:
                        yield int(s)
                        s = ""
                    if c in string.whitespace: continue
                    elif c in ["+", "-", "d", "k"]: yield c
                    else: raise ValueError("Unexpected character {}".format(c))
            return

        return [(1, 20)]

    def parse_roll_expr(tokenizer):
        lhs = parse_roll(tokenizer)
        try:
            op = next(tokenizer)
            rhs = parse_roll_expr(tokenizer)
        except StopIteration:
            return lhs
        return ("+", lhs, rhs)

    def parse_roll(tokenizer):
        c = next(tokenizer)


    # Roll <dice> <sides>-sided dice
    # If <keep> is specified, only return the top <keep>
    # If <drop> is specified, return all but the bottom <drop>
    def roll(self, dice=1, sides=6, keep=0, drop=0):
        r = []
        rolls = []
        for i in range(dice):
            roll = random.randint(1, sides)
            r.append(roll)
            rolls.append((i, roll))
        rolls.sort(key=lambda roll: -roll[1])

        if keep > 0:
            rolls = rolls[0:keep]
        elif drop > 0:
            rolls = rolls[0:-drop]

        if len(rolls) < len(r):
            r = [roll for i,roll in enumerate(r) if (i, roll) in rolls]

        return r

                


