import os
import json
from werkzeug.utils import secure_filename
from flask import send_file
import shutil
from pathlib import Path
import base64

class handler:
    def __init__(self,RAG):
        self.RAG = RAG
        self.UploadFolder = 'uploads'
        self.dataFile = 'data/chats.json'
        self.pdfPath = 'papers/'
        self.outputImgdir = "./static/Retrievedimages/"
        self.audioPath = "./static/Audio/"
        self.confirmDir([self.pdfPath,self.audioPath,self.UploadFolder])
        
        
    def confirmDir(self,paths):
        for path in paths:
            if not os.path.exists(path):
                os.makedirs(path)

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
    
    def retreivePDFContent(self,pdfPath):
        def encode_image(image_path):
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        pdf_name = Path(pdfPath).stem
        imageDir = os.path.join(self.outputImgdir,pdf_name)
        content = [
        {
          "type": "text",
          "text": "you have every page of a given research paper, return the summary pagewise seperated by a line in the form of a lecture, dont start with page1,2 etc, try to finish the entire lecture within 1-2 minutes. dont add any special characters. return a plain string."
        },
      ]
        images = os.listdir(imageDir)
        for path in images:
            image_path = os.path.join(imageDir,path)
            base64_image = encode_image(image_path)
            data = {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }
                }
            content.append(data)
        return content,pdf_name
    
    def saveAudio(self,audio,name):
        path = os.path.join(self.audioPath,name)
        audio.save(path+".mp3")
        return path