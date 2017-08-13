from pineapple import PineappleBot, interval
import nltk

def get_tagged_word(w):
    return nltk.pos_tag(nltk.word_tokenize(w))[0]

def make_noun_file():
  with open("words_all.txt", "r") as f:
    with open("words_nouns.txt", "w") as g:
      for line in f:
          word = line.split("\t")[0]
          if (len(word) <= 2): continue
          if ('a' not in word and 
              'e' not in word and 
              'i' not in word and 
              'o' not in word and 
              'u' not in word): 
            continue
          word,tag = get_tagged_word(word)
          if len(word) > 2 and (tag == 'NN' or tag == 'NNS'):
              print(word, file=g)

def get_line(f, n):
  for i, line in enumerate(f):
    if i == n: return line.strip()
  return None

  #make_noun_file()
  
def jort(w):
    while (w[0] not in "aeiou"): w = w[1:]
    return "j" + w

class jorts(PineappleBot):
    def init(self):
        self.line = 0

    def start(self):
        self._words = open("words_nouns_40k.txt", "r") 

    def stop(self):
        self._words.close()

    @interval(60)
    def jort(self):
        word = get_line(self._words, self.line)
        if (word == None): 
          self.line = 0
          self._words.seek(0)
          word = get_line(self._words, 0)

        jord = jort(word)
        self.line += 1

        print("%s (jean %s)" % (jord, word))
        #self.toot("%s (jean %s)" % (jord, word))

