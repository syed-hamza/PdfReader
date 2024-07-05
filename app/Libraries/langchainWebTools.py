#all required tools

import requests
from Libraries.RAGHandler import RAGHandler
class agentTools:
    def __init__(self,agent):
        self.actions = []
        self.agent = agent
        self.answer = ""
        self.handler = RAGHandler()

    def getAnswer(self):
        answer = self.answer
        self.answer = ''
        return answer

    def returnActions(self,):
        actions = self.actions
        self.actions = []
        return actions
    
    def errorActions(self,):
        self.actions.append({"addMessage":{'input':self.agent.getUserQuery(),'response':"No data found in archive"}})

    def displayPdf(self,url:str):
        ''' this is a function definition
        arg1 (str): url of the retreived PDF from arxiv

        displays or shows the PDF to the user, does not return anything
        self.tools.displayPdf(URL)
        '''
        if(url==None):
            self.errorActions()
            return
        self.actions.append({"display":url})
        
    def CreateNewChat(self):
        ''' this function creates a new conversation for the user.
          Caution: call this only if the user requests to start a new conversation. dont not call this function unless you are sure. Try to avoid this unless you are 100% convinced user wants to start an entirely new conversation.
            needs no arguments
            creates a new chat for the user
            does not return anything
        '''
        self.actions.append({"newChat":""})

    def answerUser(self,answer:str):
        ''' this function returns a text response to the user.
            answer (str): Your answer in python string format only. Make sure the answer is generated from the data u recieved from the tool and summarize it enough to fit in 1-2 sentences.
            
            shows/displays your answer to the user 
            does not return anything
        '''
        if(answer==None):
            self.errorActions()
            return
        self.answer = answer
        self.actions.append({"addMessage":{'input':self.agent.getUserQuery(),'response':answer}})