from gtts import gTTS
import os

class gttsconverter():
    def __init__(self,handler):
        self.language = 'en'
        self.handler = handler

    def textToAudio(self, text,name):
        myobj = gTTS(text=text, lang=self.language, slow=False)
        return self.handler.saveAudio(myobj,name)