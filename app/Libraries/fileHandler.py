import os
import json
from werkzeug.utils import secure_filename

class handler:
    def __init__(self):
        self.UploadFolder = 'uploads'
        os.makedirs(self.UploadFolder, exist_ok=True)
        self.dataFile = 'data/chats.json'

    def load_conversations(self):
        if os.path.exists(self.dataFile):
            with open(self.dataFile, 'r') as file:
                return json.load(file)
        return []
    
    def save_conversations(self,conversations):
        with open(self.dataFile, 'w') as file:
            json.dump(conversations, file)

    def saveFile(self,file):
        filename = secure_filename(file.filename)
        filepath = os.path.join(self.UploadFolder, filename)
        file.save(filepath)
        return filepath
