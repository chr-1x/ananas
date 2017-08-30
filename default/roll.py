import random, string, itertools, traceback
from more_itertools import peekable
from ananas import PineappleBot, reply, html_strip_tags

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
    class AbortedParseError(Exception): pass

    def expect(gen, pred): 
        val,ws = gen.peek()
        if (not pred(val,ws)): raise AbortedParseError("parse got unexpected value {} in {}".format(val, pred.__code__))
        return next(gen)[0]

    def tokenizer():
        s = ""
        ws = False
        for c in text:
            if c in string.digits: s += c
            else:
                if len(s) > 0:
                    yield int(s), ws
                    s = ""
                    ws = False
                if c in string.whitespace: ws = True; continue
                elif c in ["+", "-", "*", "d", "k", ";", ",", "\n"]: yield c, ws; ws = False
                elif c == '\U0001F4AF': yield 100, ws; ws = False
                else: yield 'z', ws; ws = False
        if len(s) > 0:
            yield int(s), ws
        return

    def parse_roll_list(tokens):
        rolls = []
        try:
            roll = parse_roll_expr(tokens)
            if (roll[0] != 'c'):
                rolls.append(roll)
        except AbortedParseError as e: pass #print(repr(e))
        except ValueError as e: pass #print(repr(e))

        while True:
            try:
                next(tokens)
                roll = parse_roll_expr(tokens)
                if (roll[0] != 'c'):
                    rolls.append(roll)
            except StopIteration: break
            except AbortedParseError as e: continue #print(repr(e)); continue
            except ValueError as e: continue #print(repr(e)); continue

        return rolls

    def parse_roll_expr(tokens):
        lhs = parse_roll(tokens)
        try: 
            op = expect(tokens, lambda t,ws: t in ['+', '-', '*'])
            rhs = parse_roll_expr(tokens)
        except AbortedParseError: return lhs
        except StopIteration: return lhs
        return (op, lhs, rhs)

    def parse_roll(tokens):
        p,ws = peek(tokens)
        if (p == 'd'): c = -1
        else: c = expect(tokens, lambda t,ws: isinstance(t, int))

        try:
            d = expect(tokens, lambda t,ws: t == 'd')
            sides = expect(tokens, lambda t,ws: isinstance(t, int) and not ws)
        except AbortedParseError:
            return ('c', c)
        except StopIteration: 
            if c < 0: raise ValueError() # lone 'd'
            return ('c', c)

        if (c < 0): return ('r', 1, sides)

        try:
            dk = expect(tokens, lambda t,ws: t == 'd' or t == 'k')
            num = expect(tokens, lambda t,ws: isinstance(t, int))
        except StopIteration: 
            return ('r', c, sides)
        except AbortedParseError:
            return ('r', c, sides)

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
        if len(r) == 4 and ((r[2] == 'd' and r[3] < r[0]) or (r[2] == 'k' and r[3] > 0)):
            s += "{}{}".format(r[2], r[3])
        return s
    elif spec[0] in ['+', '-', '*']:
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
    elif spec[0] in ['+', '-', '*']:
        return (spec[0], roll_dice(spec[1]), roll_dice(spec[2]))
    else: raise ValueError("Invalid dice specification")

def sum_dice(spec):
    """ Replace the dice roll arrays from roll_dice in place with summations of
    the rolls. """
    if spec[0] == 'c': return spec[1]
    elif spec[0] == 'r': return sum(spec[1])
    elif spec[0] in ['+', '-', '*']:
        return (spec[0], sum_dice(spec[1]), sum_dice(spec[2]))
    else: raise ValueError("Invalid dice specification")

def eval_dice(spec):
    if spec[0] == 'c': return spec[1]
    elif spec[0] == 'r': return sum(spec[1])
    elif spec[0] == '+': return eval_dice(spec[1]) + eval_dice(spec[2])
    elif spec[0] == '-': return eval_dice(spec[1]) - eval_dice(spec[2])
    elif spec[0] == '*': return eval_dice(spec[1]) * eval_dice(spec[2])
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
def perform_roll(dice=1, sides=6, keep=-1, drop=-1):
    r = []
    rolls = []
    if sides == 0: 
        raise SillyDiceError("I don't have any zero-dimensional constructs but when I find one, I'll get back to you.")
    for i in range(dice):
        roll = random.randint(1, sides)
        r.append(roll)
        rolls.append((i, roll))
    rolls.sort(key=lambda roll: -roll[1])

    if keep > 0:
        rolls = rolls[0:keep]
    elif drop > 0 and drop < dice:
        rolls = rolls[0:-drop]
    elif drop == -1 and keep == -1: pass
    else:
        raise SillyDiceError("Whoops, dropped all the dice")

    if len(rolls) < len(r):
        r = [roll for i,roll in enumerate(r) if (i, roll) in rolls]

    return r

class DiceBot(PineappleBot):
    @reply
    def handle_roll(self, mention, user):
        raw = html_strip_tags(mention["content"]) 
        username = user["acct"]

        self.log("handle_roll", "Parsing dice in '{}' from @{}" .format(raw, username))
        message = ""
        try:
            rolls = parse_dice(raw)
        except Exception as e:
            self.report_error("{}\n{}".format(repr(e), traceback.format_exc()))
            rolls = []

        if len(rolls) == 0:
            rolls = [('r', 1, 6)]
            message = "I'm confused, so I'm just going to roll a d6.\n"
            return # TODO cheeky message?
        else:
            self.log("debug", "rolls: {}".format(rolls))

        for i, r in enumerate(rolls):
            try:
                #r = fixup_tree(r)
                line = "Rolling {}: ".format(spec_dice(r))
                dice = roll_dice(r)
                expr = sum_dice(dice)
                sum = eval_dice(dice)
                line += "{} = {}".format(visit_dice(dice), visit_sum_dice(expr))
                if (not isinstance(expr, int)):
                    line += " = {}".format(sum)
                message = line + "\n"
            except SillyDiceError as e:
                message += str(e) + "\n"

        self.mastodon.status_post("@{}\n{}".format(username, message),
                in_reply_to_id = mention["id"],
                visibility = mention["visibility"])


class SillyDiceError(Exception): pass
