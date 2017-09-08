import random
from ananas import PineappleBot, ConfigurationError, hourly, reply

def make_gram(word_array):
    return " ".join(word_array)

class NGramTextModel():
    def __init__(self, n, lines):
        self.n = n
        self.gram_dictionary = dict()
        self.build_from_lines(lines)

    def build_from_lines(self, lines):
        for line in lines:
            line = line.replace("\r", " ")
            line = line.replace("\n", " ")
            line_arr = ["^"] * self.n + [word.strip() for word in line.split()] + ["$"] * self.n

            for i in range(self.n, len(line_arr)):
                gram = make_gram(line_arr[i - self.n : i])
                word = line_arr[i]
                if (gram not in self.gram_dictionary):
                    self.gram_dictionary[gram] = []
                self.gram_dictionary[gram].append(word)
    
    def generate_sentence(self):
        sentence = self.n*["^"]
        next_gram = sentence[-self.n : ]
        while(next_gram != ["$"]*self.n):
            try:
                word_suggestion = random.choice(self.gram_dictionary[make_gram(next_gram)])
                sentence += [word_suggestion]
            except IndexError:
                break
            next_gram = sentence[-self.n : ]
        return " ".join(sentence[self.n : -self.n])

class MarkovBot(PineappleBot):
    def init():
        self.config.n = 2
    def start():
        if "corpus" not in self.config: raise ConfigurationError("MarkovBot requires a 'corpus'")
        with open(self.config.grammar_file, "r") as f:
            if f: self.model = NGramTextModel(self.config.n, f.lines())
            else: raise ConfigurationError("Couldn't open corpus file")

    @reply
    def reply(self, mention, user):
        self.mastodon.status_post("@{} {}".format(user["acct"], 
                self.model.generate_sentence()),
                in_reply_to_id = mention["id"],
                visibility = mention["visibility"])

    @hourly()
    def post(self):
        self.mastodon.toot(self.model.generate_sentence())

