import os
import json
from langchain_openai import ChatOpenAI
import qdrant_client
from flask import jsonify
import base64
import re
import openai
import requests


from Libraries.transcriber import whisperTranscriber
from Libraries.graphAgentIndexing import agent
from Libraries.fileHandler import handler
# from Libraries.videoGenerator import videoGen
from Libraries.QdrantRAGHandler import RAGHandler
from Libraries.audioGenerator import gttsconverter
from Libraries.VideoGen import videoGenMethod


file_path = './static/secretKey.json'
try:
    # Read the JSON file
    with open(file_path, 'r') as file:
        data = json.load(file)

    OPENAI_API_TOKEN = data["OpenAI"]
    os.environ["OPENAI_API_KEY"] = OPENAI_API_TOKEN
except:
    OPENAI_API_TOKEN = "YOUR_OPENAI_KEY"
    os.environ["OPENAI_API_KEY"] = OPENAI_API_TOKEN

class chatHandlerClass:
    def __init__(self,modelName = "gpt-4o-mini",tools =["arxiv"]):
        model = ChatOpenAI(model=modelName)
        self.tools = tools
        self.client = qdrant_client.QdrantClient(path="qdrant_d_app")
        self.RAG = RAGHandler(client = self.client)
        self.chatAgent = agent(model, tools,self.RAG)
        self.transcriber = whisperTranscriber()
        self.fileHandler = handler(self.RAG)
        self.videoGenerator = videoGenMethod()
        self.model = "gpt-4o-mini"
        self.audioGenerator = gttsconverter(self.fileHandler,speed=1.25)
        pass

    def load_conversations(self,username = None):
        return self.fileHandler.load_conversations()

    def getChatFilePath(self,username = None):
        return 'data/chats.json'

    def save_conversations(self,conversations):
        self.fileHandler.save_conversations(conversations)

    def load_conversations(self, username = None):
        DATA_FILE = self.getChatFilePath(username)
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as file:
                return json.load(file)
        return []
    
    def process_message_with_images(self,message):
        def replace_image(match):
            img_path = match.group(1)
            try:
                with open(img_path, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode()
                    return f'<img src="data:image/jpeg;base64,{encoded_string}" alt="Embedded Image">'
            except FileNotFoundError:
                return f'[Image not found: {img_path}]'
        
        processed_message = re.sub(r'<img src=\'(.*?)\'></img>', replace_image, message)
        return processed_message

    def GetResponse(self,user_message):
        response_actions = self.chatAgent(user_message)
        response_message = self.chatAgent.getText()
        retrieved_images = self.chatAgent.retrieved_images
        print('actions:',response_actions)
        return response_actions,response_message,retrieved_images
    
    def chat(self,conversation_id,user_message):
        conversations = self.fileHandler.load_conversations()
        for conversation in conversations:
            if conversation['id'] == conversation_id:
                response_actions,response_message,retrieved_images = self.GetResponse(user_message)

                processed_message = self.process_message_with_images(response_message)
                self.updateConversation(conversation,user_message,response_message)
                self.save_conversations(conversations)
                response = {
                    'actions': response_actions,
                    'message': processed_message,
                    'retrieved_images': retrieved_images
                }
                # print("actions:\n",response)
                return jsonify(response)
        
        return jsonify({'error': 'Conversation not found'}), 404
    
    def new_chat(self):
        conversations = self.load_conversations()
        new_conversation = {'id': len(conversations) + 1, 'messages': []}
        conversations.append(new_conversation)
        self.save_conversations(conversations)
        return new_conversation
    
    def delete_chat(self,conversation_id):
        conversations = self.load_conversations()
        conversations = [conv for conv in conversations if conv['id'] != conversation_id]
        self.save_conversations(conversations)

    def updateConversation(self,conversation,userMessage,responseMessage):
        conversation['messages'].append({'sender': 'user', 'text': userMessage})
        conversation['messages'].append({'sender': 'bot', 'text': responseMessage})

    def upload_audio(self,file,conversation_id):
        conversations = self.load_conversations()
        for conversation in conversations:
            if conversation['id'] == conversation_id:
                filepath = self.fileHandler.saveFile(file)
                user_message = self.transcriber(filepath)
                response_actions,response_message,retrieved_images = self.GetResponse(user_message)
                self.chat(conversation['id'],user_message)
                self.updateConversation(conversation,user_message,response_message)
                self.fileHandler.save_conversations(conversations)
                return jsonify(response_actions)
        return jsonify({'error': 'Conversation not found'}), 404
    
    def getPdf(self):
        return self.fileHandler.GetPdfNames()
    
    def uploadPDF(self,file):    
        filepath = self.fileHandler.savePdf(file)

    def sendPDF(self,filePath):
        return self.fileHandler.sendPDF(filePath)
    
    def videoFileExists(self,fileName):
        return self.fileHandler.videoFileExists(fileName)

    def toggleArxiv(self):
        return self.chatAgent.toggleArxiv()

    def isArxivAllowed(self):
        return self.chatAgent.isArxivAllowed()
    
    def summarizePDF(self,pdf_path):
        print("generating content")
        content,pdf_name = self.fileHandler.retreivePDFContent(pdf_path)

        headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"
        }

        payload = {
        "model": self.model,
        "messages": [
            {
            "role": "user",
            "content": content,
            }
        ],
        }
        print("generating openai response")

        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        lecture = response.json()['choices'][0]['message']['content']
        self.fileHandler.updateJSON(pdf_name,"lecture",lecture)
        print("generating audio")
        print("lecture",lecture)
        audioPath = self.audioGenerator.textToAudio(lecture,pdf_name)
        return str(lecture)
    
    def retrieveRelevantPdfImage(self,pdfname,timestamp):
        durations = self.fileHandler.getDurations(pdfname)
        pageNum = 0
        for i in range(len(durations)):
            if(durations[i]>=timestamp):
                pageNum = i
                break
        return self.fileHandler.pagePath(pdfname,pageNum+1)
    
    def getAudio(self,pdfname):
        return self.fileHandler.getAudio(pdfname)