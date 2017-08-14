import random, string, itertools, traceback
from more_itertools import peekable
from pineapple import PineappleBot, reply, html_strip_tags

def peek(gen): return gen.peek()

# DICE PARSING
# Formats we accept:
#  @roll [#]d#[±#]
#  @roll #d#d#[±#]
#  @roll #d#k#[±#]
# We also want to accept any amount of whitespace (but not other
# characters) between portions of the roll:
#  @roll 3 d20 + 2
#  @roll 3d20 k 4 - 2
#
# We'll accept multiple rolls, but only with semicolons, commas, or
# linebreaks beween them
#  @roll 2d20, 2d6
#
# Finally, we'll accept simple arithmetic expressions of rolls:
#  @roll 2d20 + 2d6 + 3
#
# The syntax tree is as follows:
# A single dice roll is a tuple:
#  ('r', <num sides>, <num dice>, ['d'/'k', <num to drop/keep>])
# An arithmetic expression is a tuple:
#  (<op>, <lhs>, <rhs>)
# Constants appearing in arithmetic expressions are:
#  ('c', <constant>)
# A series of dice rolls are a list:
# [(roll1), ...(rolln)]
#
# Example:
#  3d20k1 + d8 + 1
# becomes
#  ('+', ('r', 3, 20, 'k', 1) ('+', ('r', 1, 8), ('c', 1)))

def parse_dice(text):
    def tokenizer():
        s = ""
        for c in text:
            if c in string.digits: s += c
            else:
                if len(s) > 0:
                    yield int(s)
                    s = ""
                if c in string.whitespace: continue
                elif c in ["+", "-", "d", "k", ";", ",", "\n"]: yield c
                else: continue # we want to be error-tolerant as much as possible
                    #raise ValueError("Unexpected character {}".format(c))
        if len(s) > 0:
            yield int(s)
        return

    def parse_roll_list(tokens):
        rolls = []
        rolls.append(parse_roll_expr(tokens))
        while True:
            try:
                next(tokens)
                rolls.append(parse_roll_expr(tokens))
            except StopIteration: break
        return rolls

    def parse_roll_expr(tokens):
        lhs = parse_roll(tokens)
        try: 
            if peek(tokens) == '+' or peek(tokens) == '-':
                op = next(tokens)
            else: return lhs
        except StopIteration: return lhs
        rhs = parse_roll_expr(tokens)
        return (op, lhs, rhs)

    def parse_roll(tokens):
        p = peek(tokens)
        if (p == 'd'): c = -1
        else: c = next(tokens)
        try:
            if (peek(tokens) == 'd'):
                d = next(tokens)
                sides = int(next(tokens))
            else: return ('c', c)
        except StopIteration: 
            if c < 0: raise ValueError() # lone 'd'
            return ('c', c)
        c = abs(c)
        try:
            if peek(tokens) == 'd' or peek(tokens) == 'k':
                dk = next(tokens)
                num = int(next(tokens))
            else:
                return ('r', c, sides)
        except StopIteration: return ('r', c, sides)
        return ('r', c, sides, dk, num)

    return parse_roll_list(peekable(tokenizer()))

# Syntax tree visitors
# They only do singular roll expressions since the calling code is likely to
# want to unwrap the rolls and handle them one by one

def spec_dice(spec):
    """ Return the dice specification as a string in a common format """
    if spec[0] == 'c': 
        return str(spec[1])
    elif spec[0] == 'r':
        r = spec[1:]
        s = "{}d{}".format(r[0], r[1])
        if len(r) == 4:
            s += "{}{}".format(r[2], r[3])
        return s
    elif spec[0] == '+' or spec[0] == '-':
        return "{} {} {}".format(spec_dice(spec[1]), spec[0], spec_dice(spec[2]))
    else: raise ValueError("Invalid dice specification")

def roll_dice(spec):
    """ Perform the dice rolls and replace all roll expressions with lists of
    the dice faces that landed up. """
    if spec[0] == 'c': return spec
    elif spec[0] == 'r':
        r = spec[1:]
        if len(r) == 2: return ('r', perform_roll(r[0], r[1]))
        k = r[3] if r[2] == 'k' else 0
        d = r[3] if r[2] == 'd' else 0
        return ('r', perform_roll(r[0], r[1], k, d))
    elif spec[0] == '+' or spec[0] == '-':
        return (spec[0], roll_dice(spec[1]), roll_dice(spec[2]))
    else: raise ValueError("Invalid dice specification")

def sum_dice(spec):
    """ Replace the dice roll arrays from roll_dice in place with summations of
    the rolls. """
    if spec[0] == 'c': return spec[1]
    elif spec[0] == 'r': return sum(spec[1])
    elif spec[0] == '+' or spec[0] == '-':
        return (spec[0], sum_dice(spec[1]), sum_dice(spec[2]))
    else: raise ValueError("Invalid dice specification")

def eval_dice(spec):
    if spec[0] == 'c': return spec[1]
    elif spec[0] == 'r': return sum(spec[1])
    elif spec[0] == '+': return eval_dice(spec[1]) + eval_dice(spec[2])
    elif spec[0] == '-': return eval_dice(spec[1]) - eval_dice(spec[2])
    else: raise ValueError("Invalid dice specification")

def visit_dice(d):
    if d[0] == 'c': return str(d[1])
    elif d[0] == 'r':
        s = ""
        for v in d[1]: s += "[{}]".format(v)
        return s
    else:
        return "{} {} {}".format(visit_dice(d[1]), d[0], visit_dice(d[2]))

def visit_sum_dice(d):
    if isinstance(d, int): return str(d)
    else: return "{} {} {}".format(visit_sum_dice(d[1]), d[0], visit_sum_dice(d[2]))

# Roll <dice> <sides>-sided dice
# If <keep> is specified, only return the top <keep>
# If <drop> is specified, return all but the bottom <drop>
def perform_roll(dice=1, sides=6, keep=0, drop=0):
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

class DiceBot(PineappleBot):
    def start(self):
        pass

    @reply
    def handle_roll(self, mention, user):
        raw = html_strip_tags(mention["content"]) 
        username = user["username"]

        # TODO TEST TEST TEST
        if (username != 'chr'): return

        self.log("handle_roll", "Parsing dice in '{}' from @{}" .format(raw, username))
        message = ""
        try:
            rolls = parse_dice(raw)
        except Exception as e:
            self.report_error("{}\n{}".format(repr(e), traceback.format_exc()[:300]))
            rolls = [('r', 1, 6)]
            message = "Not sure what that means, rolling 1d6.\n"

        for i, r in enumerate(rolls):
            if (len(rolls) > 1):
                message += "Rolling {}: ".format(spec_dice(r))
            dice = roll_dice(r)
            expr = sum_dice(dice)
            sum = eval_dice(dice)
            message += "{} = {}".format(visit_dice(dice), visit_sum_dice(expr))
            if (not isinstance(expr, int)):
                message += " = {}".format(sum)
            message += "\n"

        self._mastodon.status_post("@{}\n{}".format(username, message),
                in_reply_to_id = mention["id"],
                visibility = "direct") #mention["visibility"])

