# vim:fileencoding=utf8
###
# Copyright (c) 2009, Roland Hieber
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import urllib;
import datetime;
import json;

class Mensa(callbacks.Plugin):
  """Provides the mensa command, which shows the dishes served 
  today in the Mensa."""
  pass

  additives = { "1": "mit Farbstoff", "2": "mit Konservierungsstoff",
    "3": "mit Antioxidationsmittel", "4": "mit Geschmacksverstärker",
    "5": "geschwefelt", "6": "geschwärzt", "7": "gewachst", "8": "mit Phosphat",
    "9": "mit Süßungsmittel", "10": "enthält eine Phenylalaninquelle",
    "11": "Milcheiweiß", "12": "koffeinhaltig", "13": "chininhaltig",
    "14": "mit Taurin", "S": "mit Schweinefleisch", "R": "mit Rindfleisch",
    "O": "ohne Schweinefleisch", "V": "vegetarisch" }

  weekdays = { 0: "mo", 1: "di", 2: "mi", 3: "do", 4: "fr", 5: "sa", 6: "mo" }
  weekdaysPrintable = { "mo": "Montag", "di": "Dienstag", "mi": "Mittwoch", 
      "do": "Donnerstag", "fr": "Freitag", "sa": "Samstag" }

  def __init__(self, irc):
    self.__parent = super(Mensa, self)
    self.__parent.__init__(irc)

  # mensa is one of { "kath", "beeth", "abend", "hbk" , "ptb" }
  # day is one of { "mo","di","mi","do","fr","sa","sa","tomorrow","today" }
  # return list of strings or False in case of error
  def _mensa(self, mensa = None, day = None, multiline = False):
    hour = datetime.datetime.now().time().hour

    if mensa == "3":
      return [ "türkis Döner:", "Dönertasche: 3,50€", "Dönerbox: 2,50€" ]

    # TODO move checks to mensa() so this function only loads the data
    # check mensa
    if mensa == None:
      # show abendmensa from 3pm to 8pm
      if hour >= 15 and hour < 20 and day == None:
        mensa = "abend"
      elif hour >= 20 and day == None:
        day = "tomorrow"
        mensa = "kath"
      else:
        mensa = "kath"
  
    # check day
    if day == None:
      day = "today";

    if day == "today":
      dow = self.weekdays[datetime.datetime.now().weekday()]
    elif day == "tomorrow":
      dow = self.weekdays[(datetime.datetime.now().weekday() + 1) % 7]
    else:
      dow = day

    #print "_mensa(): mensa=%s, dow=%s" % (mensa, dow)

    # all input is evil
    if dow not in ["mo","di","mi","do","fr","sa"]:
      return False
    if mensa not in ["kath", "beeth", "abend", "hbk", "ptb"]:
      return False

    # saturdays only in kath, otherwise http 404
    if dow == "sa" and mensa != "kath":
      return [ "Nothing." ]
    
    #Now featuring PTB-Casino too
    if mensa == "ptb":
      url = "https://blog.ktrask.de/ptbmoku.json"
      data = json.loads(urllib.urlopen(url).read())
      #python3: data = json.loads(urllib.request.urlopen(url).read().decode("utf-8"))
      utf8_data = map(lambda w: map(lambda d: d.encode("utf8"), w), data[0:5])
      ptbgerichte = { 'mo': utf8_data[0], 'di': utf8_data[1], 'mi': utf8_data[2], \
          'do': utf8_data[3], 'fr': utf8_data[4] }

      heading = "PTB-Casino am " + self.weekdaysPrintable[dow] + ": "
      if multiline:
        rply = [heading] + ptbgerichte[dow]
      else:
        rply = [heading + ' // '.join(ptbgerichte[dow])]
      return rply

    urlpart = mensa
    if mensa == "abend":
      urlpart = "kath"
  
    # fetch data from external site
    urlfile = dow + ".csv"
    url = "http://www.trivalg.de/mensa/" + urlpart + "/" + urlfile
    
    #print "Fetching "+url
    f = urllib.urlopen(url)
    s = f.read()
    #s = s.decode('iso-8859-1').encode('utf-8')
    f.close()
  
    # kath and abend are in the same file, so look for Mittagsmensa / Abendmensa
    newlines = []
    for line in s.splitlines():
      if line == "Mittagsmensa":
        continue
      if line == "Abendsmensa":
        if mensa != "abend":
          break
        elif mensa == "abend":
          newlines = []
          continue
      newlines.append(line)
  
    # build list with reply string
    heading = ""
    if mensa == "beeth":
      heading = "Mensa Beethovenstraße"
    elif mensa == "hbk":
      heading = "Mensa HBK"
    elif mensa == "kath":
      heading = "Mensa Katharinenstraße"
    elif mensa == "abend":
      heading = "Abendmensa Katharinenstraße"

    heading += " am " + self.weekdaysPrintable[dow] + ": "
    rply = [ heading ];
    
    for line in newlines:
      if line.startswith("Gibt es nicht"):
        return [ "Nothing." ]
      cols = line.split(';')
      if len(cols) > 1:
        if multiline:
          rply.append(cols[0].strip() + " " + cols[2].strip() + "€")
        else:
          rply.append(cols[0].strip() + " " + cols[2].strip() + "€ //")

    return rply

  def mensa(self, irc, msg, args, argstring):
    """[<mensa>] [<time>]

    Shows the dishes served today in <mensa>. <mensa> is one of "kath"
    (default) for Mensa 1 (Katharinenstraße), "beeth" for Mensa 2 
    (Beethovenstraße), "hbk" for Mensa HBK, "abend" for Abendmensa
    (Katharinenstraße, default for times between 3pm and 8pm) or "ptb" for
    PTB-Casino.
    <time> specifies the time to show, can be one of "mo", "di", "mi", "do",
    "fr", "sa" for the respective weekdays, or "today"/"heute" (default),
    "tomorrow"/"morgen" for todays resp. tomorrows dishes. From 8pm on, the 
    dishes for the next day are shown.
    """

    multiline = self.registryValue('multiline', 
      plugins.getChannel(msg.args[0]));

    # parse parameters if given
    day = None
    mensa = None
    if argstring and len(argstring) > 0:
      arglist = argstring.split(" ")
      for argn in arglist:
        # translate to english :P
        if argn.strip() == "morgen":
          day = "tomorrow"
        elif argn.strip() == "heute":
          day = "today"
        elif argn.strip() in ["mo","di","mi","do","fr","sa","today","tomorrow"]:
          day = argn;

        if argn.strip() in ["kath","beeth","abend","hbk","3","ptb"]:
          mensa = argn;
        elif argn.strip().rfind("1") != -1:
          mensa = "kath";
        elif argn.strip().rfind("2") != -1:
          mensa = "beeth";

    #print "calling mensa with mensa=%s,day=%s,multiline=%d" % (mensa, day, multiline)

    rply = self._mensa(mensa, day, multiline)

    if rply == False:
      irc.reply("Error in parameters. See help for this command.")
      return

    # do reply
    if multiline:
      for s in rply:
        irc.reply(s, prefixNick = False)
    else:
      irc.reply(" ".join(rply), prefixNick = False)

  mensa = wrap(mensa, [additional('text')])

  #def zusatz(self, irc, msg, args):
  #zusatz = wrap(zusatz, [])

Class = Mensa


# vim:set shiftwidth=2 tabstop=2 expandtab textwidth=79:
