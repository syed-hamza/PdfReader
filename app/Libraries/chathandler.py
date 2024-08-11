import os
import json
from langchain_openai import ChatOpenAI
import qdrant_client
from Libraries.transcriber import whisperTranscriber
from Libraries.graphAgentIndexing import agent
from Libraries.fileHandler import handler
from flask import jsonify
import base64
import re
from Libraries.QdrantRAGHandler import RAGHandler

class chatHandlerClass:
    def __init__(self,modelName = "gpt-4o-mini",tools =["arxiv"]):
        model = ChatOpenAI(model=modelName)
        self.tools = tools
        self.client = qdrant_client.QdrantClient(path="qdrant_d_app")
        self.RAG = RAGHandler(client = self.client)
        self.chatAgent = agent(model, tools,self.RAG)
        self.transcriber = whisperTranscriber()
        self.fileHandler = handler(self.RAG)
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
    
    def toggleArxiv(self):
        return self.chatAgent.toggleArxiv()

    def isArxivAllowed(self):
        return self.chatAgent.isArxivAllowed()