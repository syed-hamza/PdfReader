from gtts import gTTS
import os
from mutagen.mp3 import MP3
from pydub import AudioSegment
import re

class gttsconverter():
    def __init__(self, handler, speed=1.0):
        self.language = 'en'
        self.handler = handler
        self.speed = speed  # Speed factor

    def textToAudio(self, text, name):
        durations = []
        files = []
        text = re.sub(r'[^a-zA-Z0-9\s]', '', text)

        individualPages = [i for n, i in enumerate(text.split("\n"))]
        for n, text in enumerate(individualPages):
            if(text==""):
                continue
            myobj = gTTS(text=text, lang="en", slow=False)
            filename = f"./temp/test_{n}.mp3"
            myobj.save(filename)
            
            # Adjust the speed of the audio using pydub
            audio = AudioSegment.from_file(filename)
            if self.speed != 1.0:
                audio = audio.speedup(playback_speed=self.speed)

            audio.export(filename, format="mp3")

            mp3_audio = MP3(filename)
            duration = mp3_audio.info.length
            durations.append(duration)
            files.append(filename)

        return self.handler.MergeAndSaveAudioAndDuration(files, name, durations)