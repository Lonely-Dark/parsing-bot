# -*- coding: utf-8 -*-

# ---Lonely_Dark edit---
# Python 3.9.6

import asyncio
import threading
from queue import LifoQueue
from configparser import ConfigParser

import requests

import vk
import lang

config = ConfigParser()
config.read('conf.cfg')
token = config['DEFAULT']['token']
name = 0
stack = LifoQueue()


class Bot:
    def pin_audio_attachment(self, text, vkapi, peer_id):
        # For answers check the https://vk.com/dev/upload_files_3
        # (12's checkpoint)
        with open(f"sounds/{text}.ogg", 'rb') as f:
            data = {'file': f}

        link = vkapi.get('docs.getMessagesUploadServer',
                         peer_id=peer_id,
                         type='audio_message')
        link = link['response']['upload_url']
        load_file = requests.post(link, files=data).json()
        fileid = load_file['file']
        fileid = vkapi.get('docs.save', file=fileid, title=text+'.ogg')
        fileid = fileid['response']['audio_message']

        return f"doc{fileid['owner_id']}_{fileid['id']}_{fileid['access_key']}"


class Krem():
    def __init__(self, vkapi, peer_id, random_id):
        self.vkapi = vkapi
        self.peer_id = peer_id
        self.random_id = random_id

    async def give_help(self):
        """ SEND ALL THE COMMANDS WHICH BOT CAN GET """
        message = '''Крем, Functions:\n
/ Get help
krem help\n
/ Get the meaning of a word
krem м/m/meaning <eng word>
/ Get the full meaning with pronunciation (other definitions)
krem фм/fm <eng word>\n
/ Get all the existing synonyms of word
krem с/s/синонимы/synonyms <eng word>
/ Get the translate of a sentence/word
krem т/t/translate <eng/rus sentence>
/ Get the pronunciation or the text
krem say <eng word/sentence>\n
// Get the chinese to russian translate and back
krem рис/fig <chinese/rus word/sentence>'''
        self.vkapi.get('messages.send', peer_id=self.peer_id, random_id=self.random_id, message=message)

    async def give_meaning(self, word, dictionary='collins'):
        language = lang.language(word)
        message = await language.define(dictionary)
        self.vkapi.get('messages.send', peer_id=self.peer_id, random_id=self.random_id, message=message)

    async def give_full_meaning(self, text, dictionary='collins'):
        """ Send all the definitions of word to the user + prononciaton """
        language = lang.language(text)
        response = await language.fdefine(dictionary)
        # sound = await language.pron()
        message = response

        # with open('sounds/%s.ogg'%(text), 'wb') as f:
        #     f.write(sound)

        # attachment = Bot.pin_audio_attachment(self, text, self.vkapi, self.peer_id)
        self.vkapi.get('messages.send', peer_id=self.peer_id, random_id=self.random_id, message=message)

    async def give_synonyms(self, text):
        language = lang.language(text)
        message = await language.give_synonyms()
        self.vkapi.get('messages.send', peer_id=self.peer_id, random_id=self.random_id, message=message)

    async def give_translate(self, text):
        language = lang.language(text)
        message = await language.translate()
        self.vkapi.get('messages.send', peer_id=self.peer_id, random_id=self.random_id, message=message)

    async def fig(self, text):
        """ Translate russian to chinese and back """
        language = lang.language(text)
        message = await language.kfig()
        self.vkapi.get('messages.send', peer_id=self.peer_id, random_id=self.random_id, message=message)

    def say(self, text):
        """ Combine different audio files into one audio message """
        global name
        for i in range(len(text)):
            language = lang.language(text[i])
            if i == 0:
                say = language.pron()
            else:
                say += language.pron()

        with open('sounds/say/%s.ogg' % (name), 'wb') as f:
            f.write(say)

        attachment = Bot.pin_audio_attachment(self, text, self.vkapi, self.peer_id)
        name += 1
        self.vkapi.get('messages.send', peer_id=self.peer_id, random_id=self.random_id, attachment=attachment)


async def handler(vkapi):
    updates = stack.get()
    print(updates)

    if updates['type'] == 'message_new':
        text = updates['object']['message']['text']
        text = text.lower().split(' ', 2)
        if len(text) > 1 and text[0] in ("krem", "крем"):
            peer_id = updates['object']['message']['peer_id']
            random_id = updates['object']['message']['random_id']
            krem = Krem(vkapi, peer_id, random_id)

            if text[1] == 'help':
                asyncio.create_task(krem.give_help())
            if text[1] in ('fig', 'рис'):
                text = text[2]
                asyncio.create_task(krem.fig(text))
            if text[1] in ('t', 'т', 'translate'):
                text = text[2]
                asyncio.create_task(krem.give_translate(text))
            if text[1] in ('fm', 'фм'):
                text = text[2]
                asyncio.create_task(krem.give_full_meaning(text))
            if text[1] == 'say':
                text = text[2]
                # krem.say(text)
                vkapi.get('messages.send', peer_id=peer_id, random_id=random_id, message="Doesnt work yet")

            if text[1] in ('m', 'м', 'meaning'):
                word = text[2]
                asyncio.create_task(krem.give_meaning(word))
            if text[1] in ('s', 'с', 'синонимы', 'synonyms'):
                word = text[2]
                asyncio.create_task(krem.give_synonyms(word))

            if len(text) > 2:
                textt = text[2].split()

            if text[1] in ("collins", "urban", "cambridge") and textt[0] in ("m", "м", "meaning", "fm", "фм"):
                command = textt[0]
                word = textt[1]
                dictionary = text[1]

                if command in ("fm", "фм"):
                    asyncio.create_task(krem.give_full_meaning(word, dictionary))
                if command in ("m", "м", "meaning"):
                    asyncio.create_task(krem.give_meaning(word, dictionary))


def get_updates(vkapi):
    """ Gets list of updates (dictionaries) from vkapi, and puts them into the stack """
    while True:
        data = vkapi.ListenLP()
        if data != []:
            for i in data:
                stack.put(i)


if __name__ == "__main__":
    vkapi = vk.vkapi(token)
    vkapi.GetLP()

    thread = threading.Thread(target=get_updates, args=(vkapi,))
    thread.start()

    while True:
        try:
            asyncio.run(handler(vkapi))
        except:
            print("Something went wrong")

        # Clear cache after script
        from streamlit import caching
        caching.clear_cache()
