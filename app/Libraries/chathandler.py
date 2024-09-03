import os
import json
from flask import jsonify
import base64
import re
import requests
import ollama
import PyPDF2

from Libraries.transcriber import whisperTranscriber
from Libraries.graphAgentIndexing import agent
from Libraries.fileHandler import handler
from Libraries.RAG.qdrantRAGHandler_CLIP_Image import RAGHandler
from Libraries.audioGenerator import gttsconverter
from Libraries.langchainWebTools import agentTools
from langchain_ollama.llms import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate

# file_path = './static/secretKey.json'
# try:
#     # Read the JSON file
#     with open(file_path, 'r') as file:
#         data = json.load(file)

#     OPENAI_API_TOKEN = data["OpenAI"]
#     os.environ["OPENAI_API_KEY"] = OPENAI_API_TOKEN
# except:
#     OPENAI_API_TOKEN = "YOUR_OPENAI_KEY"
#     os.environ["OPENAI_API_KEY"] = OPENAI_API_TOKEN

class chatHandlerClass:
    def __init__(self,tools =["arxiv"]):
        self.tools = tools
        self.RAG = RAGHandler()
        self.transcriber = whisperTranscriber()
        self.fileHandler = handler(self.RAG)
        self.image_data =[]
        self.model = OllamaLLM(base_url= "http://ollama:11434", model="llama3.1:70b")
        template = """
            You are a senior researcher tasked with answering the following question: {question}. Your response should be based solely on the provided context and any relevant parts of the conversation history. Do not use any outside knowledge or assumptions.

            Given the context provided: {context}, and the relevant conversation history: {history}, please construct a valid and specific answer. Make sure the answer is well supported and accurate. If the context does not contain sufficient information, list any topics or questions that require further research.

            Ensure that you:

            1. Use only the provided context and relevant conversation history.
            2. Avoid adding notes, disclaimers, or assumptions not supported by the context.

            Your goal is to deliver a comprehensive and contextually accurate answer.
        """

        prompt = ChatPromptTemplate.from_template(template)
        self.chain = prompt | self.model

        lectureTemplate = """

            Research Paper:{paper}

            Generate a comprehensive summary of the research paper provided. The summary should be organized into clearly defined sections by using html format highlights only like <b> with the following headings:

            <b>Introduction</b>: Begin with an introduction that provides an overview of the research topic, the main objectives of the study, and the significance of the research. Include relevant background information to set the context.

            <b>Main Findings</b>: Summarize the key findings of the research. Describe the most important results and discoveries made in the study. Highlight any novel insights or contributions to the field.

            <b>Methodology</b>: Provide a brief overview of the methods and approaches used in the research. Discuss the experimental design, data collection, and analysis techniques. Mention any tools, frameworks, or models utilized.

            <b>Discussion</b>: Interpret the findings in the context of existing research. Discuss the implications of the results, their relevance to the field, and any potential applications. Address any limitations of the study and suggest areas for future research.

            <b>Conclusion</b>: Conclude with a summary of the overall contributions of the research. Reinforce the significance of the findings and their impact on the field. Offer final thoughts on the study's broader implications.

            Citations: Where necessary, include references to key studies or previous research that support or contrast with the findings of the paper. Ensure citations are mentioned within the relevant sections. You are given image summaries but do not focus on them, you can just mention them.
        """
        lecturePrompt = ChatPromptTemplate.from_template(lectureTemplate)
        self.lectureChain = lecturePrompt | self.model


        self.agentTools = agentTools()
        # self.texthandler = texthandler()
        self.audioGenerator = gttsconverter(self.fileHandler,speed=1.25)
 
    def load_conversations(self,username = None):
        return self.fileHandler.load_conversations()

    def getChatFilePath(self,username = None):
        return 'data/chats.json'

    def save_conversations(self,conversations):
        self.fileHandler.save_conversations(conversations)

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

    def GetResponse(self,user_message,history = ''):    
        retrieved_text = self.RAG.query(user_message)
        if(isinstance(retrieved_text,dict)):
            self.image_data = retrieved_text["images"]
            print("Number of images:",len(self.image_data))
            retrieved_text = retrieved_text["text"]
        print("Context:",retrieved_text)
        print("_"*100)
        response_message = self.chain.invoke({"context":retrieved_text,"question": user_message,"history":history})
        if(len(self.image_data)>0):
            response_message =  response_message
        self.agentTools.answerUser(response_message,user_message)
        print("Answer:",response_message)
        print("_"*100)
        response_actions = self.agentTools.returnActions()

        return response_actions,response_message
    
    def chat(self,conversation_id,user_message):
        conversations = self.fileHandler.load_conversations()
        for conversation in conversations:
            if conversation['id'] == conversation_id:
                print("chat start")
                history = conversation["messages"]
                response_actions,response_message = self.GetResponse(user_message,history)
                self.updateConversation(conversation,user_message,response_message)
                self.save_conversations(conversations)
                response = {
                    'actions': response_actions,
                    'numImages':len(self.image_data)
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
                # print("transcribed: ",user_message)
                response_actions,response_message = self.GetResponse(user_message)
                self.chat(conversation['id'],user_message)
                self.updateConversation(conversation,user_message,response_message)
                self.fileHandler.save_conversations(conversations)
                return jsonify(response_actions)
        return jsonify({'error': 'Conversation not found'}), 404
    
    def getPdf(self):
        return self.fileHandler.GetPdfNames()
    
    def uploadPDF(self,file):    
        fileName = self.fileHandler.savePdf(file)
        return fileName

    def sendPDF(self,filePath):
        return self.fileHandler.sendPDF(filePath)
    
    def videoFileExists(self,fileName):
        return self.fileHandler.videoFileExists(fileName)

    # def toggleArxiv(self):
    #     return self.chatAgent.toggleArxiv()

    # def isArxivAllowed(self):
    #     return self.chatAgent.isArxivAllowed()
    
    # def summarizePDF(self,pdf_path): #openai
    #     savedsum = self.fileHandler.loadJSON(pdf_path,"lecture")
    #     if(savedsum !=[]):
    #         lecture = self.texthandler(savedsum)
    #         return lecture

    #     print("generating content")
    #     content,pdf_name = self.fileHandler.retreivePDFContent(pdf_path)

    #     headers = {
    #     "Content-Type": "application/json",
    #     "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"
    #     }

    #     payload = {
    #     "model": self.model,
    #     "messages": [
    #         {
    #         "role": "user",
    #         "content": content,
    #         }
    #     ],
    #     }
    #     print("generating openai response")
    #     response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    #     lecture = response.json()['choices'][0]['message']['content']
    #     self.fileHandler.updateJSON(pdf_path,"summary",lecture)
        
    #     self.fileHandler.updateJSON(pdf_name,"lecture",lecture)
    #     print("generating audio")
    #     audioPath = self.audioGenerator.textToAudio(lecture,pdf_name)
    #     print("HTML friendly lecture")
    #     lecture = self.texthandler(lecture)
    #     print("lecture:",lecture)
    #     return lecture
    
    def summarizePDFOllama(self,pdfName):
        savedsum = self.fileHandler.loadJSON(pdfName,"lecture")
        # if(savedsum !=[]):
        #     lecture = self.texthandler(savedsum)
        #     return lecture

        print("generating content")
        pdfPath = os.path.join(self.fileHandler.pdfPath,pdfName)
        


        retrieval_results = self.RAG.getAllPdfText(pdfName)
        lecture = self.lectureChain.invoke({"paper":retrieval_results})
        self.fileHandler.updateJSON(pdfName,"lecture",lecture)
        print("generating audio")
        audioPath = self.audioGenerator.textToAudio(lecture,pdfName)
        lecture = self.texthandler(lecture)
        # self.updateConversation(self,conversation,userMessage,responseMessage)
        return lecture
    
    def texthandler(self,text):
        paragraphs = [para.strip() for para in text.split('\n') if para.strip()]
        html_output = ""
        for i, paragraph in enumerate(paragraphs, 1):
            html_output += f'<div id="paragraph-{i}">{paragraph}</div>\n'
        return html_output

    def retrieveRelevanclassName(self, pdfname,timestamp):
        durations = self.fileHandler.getDurations(pdfname)
        pageNum = 0
        for i in range(len(durations)):
            if(durations[i]>=timestamp):
                pageNum = i
                break
        return str(pageNum+1)

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
    
    def getImage(self,num):
        if num>=len(self.image_data):
            return None
        return self.image_data[num]
    
    def getImageHTML(self,num):
        if num>=len(self.image_data):
            return None
        return f"""<img src="{self.image_data[0]}" alt="Retrieved Image"></br>"""
    
    def queryImage(self,base64Img):
        return self.RAG.getDataFromBase64Image(base64Img)