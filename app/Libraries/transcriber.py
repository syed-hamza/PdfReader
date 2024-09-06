import subprocess
import os
from transformers import pipeline
import torch
# import openai


# class whisperTranscriber():
#     def __init__(self):
#         self.model = "whisper-1"

#     def __call__(self,audioPath):
#         print(audioPath)
#         return self.transcribe(audioPath)
    
#     def transcribe(self,audio_file):
#         audio_file= open(audio_file, "rb")
#         transcript = openai.audio.transcriptions.create(
#             model=self.model, 
#             file=audio_file,
#             response_format="text")
#         return transcript

class whisperTranscriber():
    def __init__(self):
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.pipe = pipeline(
            "automatic-speech-recognition",
            model="openai/whisper-medium.en",
            chunk_length_s=100,
            device=self.device,
        )
    def __call__(self,audioPath):
        return self.transcribe(audioPath)
    
    def transcribe(self,audio_file):
        transcription = self.pipe(audio_file)['text']
        return transcription