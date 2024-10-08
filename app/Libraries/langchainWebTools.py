#all required tools


class agentTools:
    def __init__(self,agent = None):
        self.actions = []
        self.agent = agent
        self.answer = ""


    def getAnswer(self):
        answer = self.answer
        self.answer = ''
        return answer

    def returnActions(self,):
        actions = self.actions
        self.actions = []
        return actions
    
    def errorActions(self,):

        self.actions = [{"addMessage":{'input':self.agent.getUserQuery(),'response':"No data found in archive"}}]

    def displayPdf(self,url):
        ''' this is a function definition
        arg1 (str): url of the retreived PDF from arxiv only. DO NOT PUT ANY IMAGE PATH or it will be ignored. PDF ONLY.

        displays the PDF to the user, does not return anything. Call this when users asks you to show or display any paper, do not class otherwise.
        Usage:
        self.tools.displayPdf(URL) 
        '''
        if url == None:
            self.errorActions()
            return
        if(url[-3:]=="pdf"):
            self.actions.append({"display":url})
        else:
            self.errorActions()
        
    def CreateNewChat(self):
        ''' this function creates a new conversation for the user.
          Caution: call this only if the user requests to start a new conversation. dont not call this function unless you are sure. Try to avoid this unless you are 100% convinced user wants to start an entirely new conversation.
            needs no arguments
            creates a new chat for the user
            does not return anything
        '''
        self.actions.append({"newChat":""})

    def answerUser(self,answer, question = ''):
        ''' this function returns a text response to the user. This action should only be taken once.
            answer (str): Your detailed answer in python string format only. Make sure the answer is generated from the data you recieved from the tool.
            Returning this function is a must. If the user asks only for the research paper, just answer "Sure" or other accepting phrases.
            Try highlighting important parts of the answer using html <b></b> and leaving a line after every paragraph. Make the asnwer as detailed as possible based on the context.
            
            shows/displays your text answer to the user 
            does not return anything
        '''
        if answer is None:
            self.errorActions()
            return
        self.answer = answer
        if question =='':
            self.actions.append({"addMessage":{'input':self.agent.getUserQuery(),'response':answer}})
        else:
            self.actions.append({"addMessage":{'input':question,'response':answer}})