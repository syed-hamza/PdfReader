import subprocess
import os
import openai

class whisperTranscriber():
    def __init__(self):
        self.model = "whisper-1"

    def __call__(self,audioPath):
        print(audioPath)
        return self.transcribe(audioPath)
    
    def transcribe(self,audio_file):
        audio_file= open(audio_file, "rb")
        transcript = openai.audio.transcriptions.create(
            model=self.model, 
            file=audio_file,
            response_format="text")
        return transcript