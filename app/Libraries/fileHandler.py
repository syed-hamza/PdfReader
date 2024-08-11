import os
import json
from werkzeug.utils import secure_filename
from flask import send_file
import shutil

class handler:
    def __init__(self,RAG):
        self.RAG = RAG
        self.UploadFolder = 'uploads'
        os.makedirs(self.UploadFolder, exist_ok=True)
        self.dataFile = 'data/chats.json'
        self.pdfPath = 'papers/'

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
    
    def savePdf(self,file):
        filename = secure_filename(file.filename)
        filepath = os.path.join(self.pdfPath, filename)
        file.save(filepath)
        self.RAG.postProcess(filepath)
        return filepath
    
    def GetPdfNames(self):
        return list(os.listdir(self.pdfPath))

    def clearPDF(self,directory_path):
        for filename in os.listdir(directory_path):
            file_path = os.path.join(directory_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')

    def sendPDF(self,filePath):
        path = os.path.join(self.pdfPath,filePath)
        print(path)
        return send_file(path, mimetype='application/pdf')