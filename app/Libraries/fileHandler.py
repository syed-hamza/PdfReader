import os
import json
from werkzeug.utils import secure_filename
from flask import send_file
import shutil
from pathlib import Path
from pydub import AudioSegment
import base64
import json

class handler:
    def __init__(self,RAG):
        self.RAG = RAG
        self.UploadFolder = 'uploads'
        self.dataFile = 'data/chats.json'
        self.pdfPath = 'papers/'
        self.outputImgdir = "./static/Retrievedimages/"
        self.audioPath = "./static/Audio/"
        self.logPath = "./logs/"
        self.tempPath = "./temp/"
        self.videoPath = './static/results/'
        self.SeperateImgDir = "./static/Retrievedimages/"
        self.confirmDir([self.pdfPath,self.audioPath,self.UploadFolder,self.logPath,self.tempPath,self.videoPath,self.SeperateImgDir])
        
    def updateJSON(self,name,title,data):
        if(name[:-4]==".pdf"):
            name = Path(name).stem
        filePath = os.path.join(self.logPath,name+".json")
        with open(filePath, 'w+') as file:
            try:
                filedata = json.load(file)
                filedata[title] = data
                json.dump(fileData, file, indent=4) 
            except:
                fileData = {title:data}
                json.dump(fileData, file, indent=4) 
            
        
        
    def loadJSON(self,name,title):
        filePath = os.path.join(self.logPath,name+".json")
        if(not os.path.exists(filePath)):
            print("log file not found for :",filePath)
            return []
        else:
            with open(filePath, 'r') as file:
                filedata = json.load(file)
                return filedata[title]
            
    def videoFileExists(self,fileName):
        fileName = os.path.join(self.videoPath,self.fileName[:-4]+".mp4")
        if(os.path.exists(fileName)):
            return True
        return False

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
          "text": "you have every page of a given research paper, return the summary pagewise seperated by a line in the form of a lecture, dont start with page1,2 etc, try to finish the entire lecture within 3-5 minutes and dont forget to explain relevant tables and images. dont add any special characters. return a plain string."
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
    
    def MergeAndSaveAudioAndDuration(self,files,name,durations):
        combined = AudioSegment.from_mp3(files[0])
        for mp3_file in files[1:]:
            audio_segment = AudioSegment.from_mp3(mp3_file)
            combined += audio_segment

        combined.export(name+".mp3", format='mp3')
        sm = 0
        cumdur = []
        for i in durations:
            sm += i
            cumdur.append(sm)
        self.updateJSON(name,"duration",cumdur)
        return name+".mp3"
    
    def getDurations(self,name):
        if(name[-4:]==".pdf"):
            name = Path(name).stem
        data = self.loadJSON(name,"duration")
        if(not isinstance(data,str)):
            return data
        return eval(data)
    
    def pagePath(self,pdfname,pageNum):
        if(pdfname[-4:]==".pdf"):
            pdfname = Path(pdfname).stem
        return os.path.join(self.SeperateImgDir,pdfname,str(pageNum)+".png")
