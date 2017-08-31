import json, random
from ananas import PineappleBot, ConfigurationError, hourly, reply

def _split_delimited(str, sep, inside=False):
    s = str.partition(sep)
    if s[1] == sep:
        if inside: return [sep + s[0]] + _split_delimited(s[2], sep, False) 
        else: return ([s[0]] if s[0] else []) + _split_delimited(s[2], sep, True)
    elif inside: raise ValueError("Uneven number of separators")
    else: return [str] if str else []

class TraceryGrammar():
    """ Class representing the runtime tree of a tracery grammar for easy
    evaluation. """

    class Symbol():
        def __init__(self, sym):
            parts = sym.partition(".")
            self.nonterminal = parts[0]
            self.filter = parts[2]

        def eval(self, grammar):
            return grammar.filter(grammar.eval(self.nonterminal), self.filter)

        def __str__(self):
            return "<symbol: {}{}>".format(self.nonterminal, " <- {}".format(self.filter) if self.filter else "")

    def __init__(self, json_dict):
        self.nonterminals = json_dict
        for n,expansion in self.nonterminals.items():
            for i,option in enumerate(expansion):
                try:
                    symbols = _split_delimited(option, "#")
                except ValueError as e:
                    raise ValueError("In {}: {}".format(option, e))
                for j,s in enumerate(symbols):
                    if s[0] == "#":
                        symbols[j] = TraceryGrammar.Symbol(s[1:])
                expansion[i] = symbols

    def filter(self, phrase, func):
        if func == "": return phrase
        if func == "a": return ("an " if phrase[0] in "aeiou" else "a ") + phrase
        if func == "capitalize": return phrase.capitalize()
        if func == "capitalizeAll": return " ".join([w.capitalize() for w in phrase.split(" ")])
        if func == "s": 
            if phrase[-1] == "y": return phrase[:-1] + "ies"
            return phrase + "s"
        if func == "ed": 
            if phrase[-1] == "y": return phrase[:-1] + "ied"
            else: return phrase + "ed"
        raise ValueError("Unknown filter {}".format(func))

    def eval(self, sym):
        options = self.nonterminals[sym]
        expansion = random.choice(options)
        return "".join([s.eval(self) if isinstance(s, TraceryGrammar.Symbol) else s for s in expansion])

    def __str__(self):
        r = ""
        for n, os in self.nonterminals.items():
            r += "{}:\n".format(n)
            for o in os:
                r += "    "
                for s in o:
                    r += "{}, ".format(str(s))
                r += "\n"
        return r

class TraceryBot(PineappleBot):
    def init(self):
        self.config.root_symbol = "origin"

    def start(self):
        if "grammar_file" not in self.config: raise ConfigurationError("TraceryBot requires a 'grammar_file'")
        if "root_symbol" not in self.config: raise ConfigurationError("TraceryBot requires a 'root_symbol'")
        with open(self.config.grammar_file, "r") as f:
            if f: self.grammar = TraceryGrammar(json.load(f))
            else: raise ConfigurationError("Couldn't open grammar file")

    @reply
    def post(self, mention, user):
        self.mastodon.status_post("@{} {}".format(user["acct"], 
                self.grammar.eval(self.config.root_symbol)),
                in_reply_to_id = mention["id"],
                visibility = mention["visibility"])

    @hourly()
    def post(self):
        self.mastodon.toot(self.grammar.eval(self.config.root_symbol))
