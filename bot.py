from fbchat import Client
from fbchat.models import *

import random
import json
import re

import time 

import dateparser
import datetime
import argparse
import shlex

regex = re.compile("[0-9]*#")   # search for events

addParser = argparse.ArgumentParser()

addParser.add_argument("-t", action = "store", default = "")
addParser.add_argument("-e", action = "store", default = "", required = "True")
addParser.add_argument("-l", action = "store", default = "")
addParser.add_argument("-d", action = "store", default = "")


amendParser = argparse.ArgumentParser()

amendParser.add_argument("-t", action = "store", default = -1)
amendParser.add_argument("-e", action = "store", default = -1)
amendParser.add_argument("-l", action = "store", default = -1)
amendParser.add_argument("-d", action = "store", default = -1)
    
def parse(cmd, parser):
    lex = shlex.split(cmd)

    namespace = parser.parse_args(lex)
    return namespace

def matchBeginning(cmd, match):
    return cmd[:len(match)] == match


class BotClient(Client):
    def __init__(self, username, password, init_path = "config.json", session_cookies = ""):
        super().__init__(username, password, session_cookies = session_cookies)
        
        with open(init_path, 'r') as f:
            self.config = json.loads(f.read())
        
        print(self.config)

        # these are people who have permissions to edit events
        self.user_id_whitelist = []

        for thread in self.config['user_whitelist']:
            thread_ = self.getThread(thread)

            if thread_:
                uid = thread_.uid
                self.user_id_whitelist.append(uid)
                self.config['uids'][uid] = thread
      
        self.current_events = self.config['events']
        self.number_of_events = len(self.current_events)

        self.init_path = init_path
    
        print(self.config)

        self.updateConfig()

    def getThread(self, name):
        thread = self.searchForThreads(name)
        if thread:
            return thread[0]

    def updateConfig(self):
        self.number_of_events = len(self.current_events)
        
        with open(self.init_path, 'w') as f:
            f.write(
                json.dumps(self.config)
            )

    def generateEventsString(self):
        res = ""
        for i, event in enumerate(self.current_events):
            res += "%s. %s\n\n" % (i, self.formatEvent(event))
        
        return res 
    
    def checkPermissions(func):
        def proxy(self, msg, author_id, thread_id, thread_type):
            if author_id not in self.user_id_whitelist:
                self.send(
                            Message(text = "sorry bron, you do not have permissions to update my events!"),
                            thread_id = thread_id, 
                            thread_type = thread_type
                        )
                return 
            
            func(self, msg, author_id, thread_id, thread_type)
        
        return proxy

    @checkPermissions
    def sudo(self, msg, author_id, thread_id, thread_type):
        
        user = msg['body'][13:]

        user_ = self.searchForUsers(user)
        if user_:
            uid = user_[0].uid
            self.config['user_whitelist'].append(user)
            self.user_id_whitelist.append(uid)
            self.config['uids'][uid] = user

            self.updateConfig()

            self.send(
                Message(text = "%s has been elevated to sudo permissions!" % user),
                thread_id = thread_id, 
                thread_type = thread_type
            )

            if (thread_id != uid):
                self.send(
                    Message(text = "you have sudo permissions for eventbot!"),
                    thread_id = uid, 
                    thread_type = ThreadType.USER
                )
    
    @checkPermissions
    def desudo(self, msg, author_id, thread_id, thread_type): 
        user = msg['body'][15:]

        user_ = self.searchForUsers(user)
        if user_:
            uid = user_[0].uid
            
            # find corresponding username
            user = self.config['uids'].get(uid)
            
            if user:
                idx = self.config['user_whitelist'].index(user)
                del self.user_id_whitelist[idx]
                del self.config['user_whitelist'][idx]

                self.updateConfig()

                self.send(
                    Message(text = "%s has been lowered to normal permissions!" % user),
                    thread_id = thread_id, 
                    thread_type = thread_type
                )

                if (thread_id != uid):
                    self.send(
                        Message(text = "you frickin noob, you no longer have sudo permissions"),
                        thread_id = uid, 
                        thread_type = ThreadType.USER
                    )
    
    def formatEvent(self, event):

        # time, location
        # -> : June 8th, 5PM @ Somerset

        # just time
        # -> : June 8th, 5PM

        # just location 
        # -> @ Somerset

        if type(event['time']) != str:      # the time was correctly parsed
            t = datetime.datetime.fromtimestamp(event['time'])
            t = t.strftime("%A, %B %d %I:%M %p (%Y)")
        else:
            t = event['time']

        res = event['event']
        if event['time'] != "":
            res += "\nwhen? " + t

        if event['location'] != "":
            res += "\nwhere? " + event['location']

        if event['details'] != "":
            res += "\n[%s]" % event['details']

        return res

    @checkPermissions
    def addEvent(self, msg, author_id, thread_id, thread_type):
        content = msg['body'][12:]
        content = content.replace('\n', ' ')

        try:
            namespace = parse(content, addParser)
        except:
            self.send(
                Message(text = "wrong syntax u naenae baby"),
                thread_id = thread_id, 
                thread_type = thread_type
            )

            return

        #event_starter = regex.match(content)
        #if event_starter:
        #    content = content[event_starter.span()[1]:]
        
        t = namespace.t
        e = namespace.e
        l = namespace.l
        d = namespace.d

        parsed_time = dateparser.parse(t)
        if not parsed_time:
            parsed_time = t
        else:
            parsed_time = parsed_time.timestamp()
            
        self.current_events.append({
            "time" : parsed_time,
            "event" : e,
            "location" : l,
            "details" : d
        })
        
        self.updateConfig()

        self.send(
            Message(text = "thanks friend! I have updated the events"),
            thread_id = thread_id, 
            thread_type = thread_type
        )

    @checkPermissions
    def amendEvent(self, msg, author_id, thread_id, thread_type):
        event_number = int(msg['body'][14])

        print("\n\n\n\n\n\n", event_number, msg['body' ])

        content = msg['body'][16:]
        content = content.replace('\n', ' ')

        try:
            namespace = parse(content, amendParser)
        except:
            self.send(
                Message(text = "wrong syntax u naenae baby"),
                thread_id = thread_id, 
                thread_type = thread_type
            )

            return

        #event_starter = regex.match(content)
        #if event_starter:
        #    content = content[event_starter.span()[1]:]
        
        t = namespace.t
        e = namespace.e
        l = namespace.l
        d = namespace.d

        parsed_time = dateparser.parse(str(t))
        if not parsed_time:
            parsed_time = t
        else:
            parsed_time = parsed_time.timestamp()
            
        if t != -1:
            self.current_events[event_number]['time'] = parsed_time
        if e != -1:
            self.current_events[event_number]['event'] = e
        if l != -1:
            self.current_events[event_number]['location'] = l
        if d != -1:
            self.current_events[event_number]['details'] = d

        self.updateConfig()

        self.send(
            Message(text = "thanks friend! I have amended the event"),
            thread_id = thread_id, 
            thread_type = thread_type
        )

    @checkPermissions
    def delEvent(self, msg, author_id, thread_id, thread_type):
        try:
            event_number = int(msg['body'][12])    
        
            del self.current_events[event_number] 
            self.updateConfig() 
            
            self.send(
                Message(text = "I 👏 have 👏 deleted 👏 the 👏 event!"),
                thread_id = thread_id, 
                thread_type = thread_type
            )

        except:
            self.send(
                Message(text = "oops! syntax error, make sure you're specifying the event number"),
                thread_id = thread_id, 
                thread_type = thread_type
            )
    
    def showEvents(self, msg, author_id, thread_id, thread_type):
        oohs = ''.join(['oO'[random.randint(0, 1)] for i in range (random.randint(5, 10))]) + "hH"[random.randint(0, 1)]
            
        self.send(
            Message(text = "%s i have %d event(s) for you:\n\n%s" % (oohs, self.number_of_events, self.generateEventsString())),
            thread_id = thread_id, 
            thread_type = thread_type
        )

    def onMessage(self, mid, author_id, message_object, thread_id, thread_type, ts, metadata, msg, **kwargs):
        
        lower = msg['body'].lower()
        oofs = lower.count('oof')

        foos = lower.count('foo')

        if matchBeginning(msg['body'], '!barackobama'):
            time.sleep(random.uniform(0.5, 1))
            oohs = ''.join(['oO'[random.randint(0, 1)] for i in range (random.randint(5, 10))]) + "hH"[random.randint(0, 1)]
            uhhs = "uU"[random.randint(0, 1)] + ''.join(['hH'[random.randint(0, 1)] for i in range (random.randint(5, 100))]) 

            self.send(
                Message(text = oohs + " " + uhhs),
                thread_id = thread_id, 
                thread_type = thread_type
            )

        elif matchBeginning(msg['body'], '!whereisnathan'):
            self.send(
                Message(text = random.choice([
                    "listening to nightcall in his car",
                    "mcdonalds",
                    "walmart",
                    "dead", 
                    "777-ZOINKS"
                ])),
                thread_id = thread_id, 
                thread_type = thread_type
            )
        
        elif matchBeginning(msg['body'], '!isthisthekrustykrab'):
            self.config['patrickCount'] += 1
            self.config['patrickCount'] = self.config['patrickCount'] % 4
            
            patrick = [
                "no, this is patrick",
                "no! this is patrick!",
                "NOO! THIS IS PATRICK! [puts phone down and folds arms]",
                "Spongebob: Uhh, patrick, that's the name of the restaurant.\nPatrick: Huh? Oh.... fishpaste!"
            ]

            self.send(
                Message(text = patrick[self.config['patrickCount']]),
                thread_id = thread_id, 
                thread_type = thread_type
            )

            self.updateConfig()

        elif msg['body'][:10] == '!oofcount':
            time.sleep(random.uniform(0.5, 1))
            
            self.send(
                Message(text = "count: %s" % (self.config['oofCount'])),
                thread_id = thread_id, 
                thread_type = thread_type
            )

        elif oofs > 0 or foos > 0:
            self.config['oofCount'] += oofs
            self.config['oofCount'] -= foos
            self.updateConfig()
            
            self.send(
                Message(text = "count: %s" % (self.config['oofCount'])),
                thread_id = thread_id, 
                thread_type = thread_type
            )


        elif msg['body'][:12] == '!events sudo':
            time.sleep(random.uniform(0.5, 1))
            self.sudo(msg, author_id, thread_id, thread_type)

        elif msg['body'][:14] == '!events desudo':
            time.sleep(random.uniform(0.5, 1))
            self.desudo(msg, author_id, thread_id, thread_type)

        elif msg['body'][:11] == '!events add':
            time.sleep(random.uniform(0.5, 1))
            self.addEvent(msg, author_id, thread_id, thread_type)

        elif msg['body'][:11] == '!events del':
            time.sleep(random.uniform(0.5, 1))
            self.delEvent(msg, author_id, thread_id, thread_type)

        elif msg['body'][:13] == '!events amend':
            time.sleep(random.uniform(0.5, 1))
            self.amendEvent(msg, author_id, thread_id, thread_type)

        elif msg['body'] == '!events':
            time.sleep(random.uniform(0.5, 1))
            self.showEvents(msg, author_id, thread_id, thread_type)


email = ""
password = ""
cookie = {}

client = BotClient(email, pass, init_path = "config.json", session_cookies= cookie)
cookies = client.getSession()
print(cookies)
client.listen()
