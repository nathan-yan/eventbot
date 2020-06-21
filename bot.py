from fbchat import Client
from fbchat.models import *

import random
import json
import re

regex = re.compile("[0-9]*#")   # search for events

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
            res += "%s# %s\n\n" % (i, event)
        
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
    
    @checkPermissions
    def addEvent(self, msg, author_id, thread_id, thread_type):
        content = msg['body'][12:]

        beginning_quote = content[0]
        ending_quote = content[1:].index(beginning_quote)

        if beginning_quote not in "\"\'":
            self.send(
                Message(text = "please surround your event in quotations!"),
                thread_id = thread_id, 
                thread_type = thread_type
            )
            return

        if not ending_quote:
            content = content[1:]
        else:
            content = content[1: ending_quote + 1]

        #event_starter = regex.match(content)
        #if event_starter:
        #    content = content[event_starter.span()[1]:]

        content = content.replace('\n', ' ')

        self.current_events.append(content)

        self.updateConfig()

        self.send(
            Message(text = "thanks friend! I have updated the events"),
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
        if msg['body'][:12] == '!events sudo':
            self.sudo(msg, author_id, thread_id, thread_type)

        elif msg['body'][:14] == '!events desudo':
            self.desudo(msg, author_id, thread_id, thread_type)

        elif msg['body'][:11] == '!events add':
            self.addEvent(msg, author_id, thread_id, thread_type)

        elif msg['body'][:11] == '!events del':
            self.delEvent(msg, author_id, thread_id, thread_type)

        elif msg['body'] == '!events':
            self.showEvents(msg, author_id, thread_id, thread_type)

email = ""
password = ""
cookie = {}

client = BotClient(email, pass, init_path = "config.json", session_cookies= cookie)
cookies = client.getSession()
print(cookies)
client.listen()