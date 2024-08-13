from gtts import gTTS
import os
from mutagen.mp3 import MP3


class gttsconverter():
    def __init__(self,handler):
        self.language = 'en'
        self.handler = handler

    def textToAudio(self, text,name):
        durations = []
        files = []
        induvidualPages = [i for n,i in enumerate(text.split("\n")) if n%2==0]
        for n,text in enumerate(induvidualPages):
            myobj = gTTS(text=text, lang="en", slow=False)
            filename = f"./temp/test_{n}.mp3"
            myobj.save(filename)
            audio = MP3(filename)
            duration = audio.info.length
            durations.append(duration)
            files.append(filename)
        
        return self.handler.MergeAndSaveAudioAndDuration(files,name,durations)