
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage
from langchain_community.tools.tavily_search import TavilySearchResults
import operator
from Libraries.langchainWebTools import agentTools
from langchain_community.agent_toolkits.load_tools import load_tools
import inspect
from langchain_core.pydantic_v1 import BaseModel
import os
import arxiv
import json
import ollama

# from Libraries.RAGHandler import RAGHandler


class AgentState(TypedDict):
    task: str
    research_plan: str
    retrieved_URLs: dict[str, str]
    generated_answer: str
    actions: List[str]
    required_info: List[str]
    iteration_count: int
    retreivedSummary: List[str]

class Queries(BaseModel):
    queries: List[str]

class Answer(BaseModel):
    answer: str
    required_info: List[str]

class Actions(BaseModel):
    actions: List[str]

class agent():
    def __init__(self, model, Searchtools,RAGHandler,AllowRequests=True):
        self.Actiontools = agentTools(self)
        self.AnswerGeneratorPrompt = """You are a senior researcher tasked with answering questions and identifying areas where more information is needed. Based on the user's question and any retrieved content, provide an answer and list any topics or questions that require further research, Use only the context provided, not your own knowledge. Make sure you list topics if the context doesnt show relevant information.

Your response should be structured as follows:
1. Answer: Provide a detailed answer to the user's question based on available information, if the user asks to display any paper put the topic in the requiredinfo. Make sure you use the context for relevant information and not make your own.
2. Required Info: If and only if a person requests any research paper(like display or show) this list should include the title of the paper. Otherwise the list should be empty. Do not put anything in the list unless you are absolutely certain a new research paper is needed. It should be empty most of the time. to call it only use definitive terms like ["Neural Networks"]
Try highlighting important parts of the answer using html <b></b> and leaving a line after every paragraph. Make the answer as detailed as possible based on the context.
Remember to be informative and accurate.Strictly follow the following output format.
output Format: {'Answer': Your answer ,'Required Info':list of information needed}."""

        self.RetreiverPrompt = """Given the research plan or required information, generate specific queries to search for on ArXiv. These queries should be focused and relevant to the topics that need more information.

Format your response as a list of search queries."""
        self.websiteActionPrompt = self.getWebsiteActionPrompt()
        self.arxivRetriever = load_tools(Searchtools)[0]
        self.model = model
        self.generateGraph()
        self.answer = ""
        self.RequestData = False
        self.AllowRequests = AllowRequests
        self.RAGHandler = RAGHandler
        self.history = ""

    def toggleArxiv(self):
        if(self.AllowRequests):
            self.AllowRequests = False
        else:
            self.AllowRequests = True
        return self.AllowRequests
    
    def isArxivAllowed(self):
        return self.AllowRequests
    
    def getText(self):
        return self.Actiontools.getAnswer()
    
    def getUserQuery(self):
        return self.prompt
    
    def getActions(self):
        return self.Actiontools.returnActions()

    def getWebsiteActionPrompt(self):
        prompt = "The following functions are already defined,these functions are called to change the users view, write the string form of python code to call the function appropriately based on what actions are required to satisfy the user based on his question and the answer, make sure its directly executable as i will run the exec function  and no error should be raised.Only return the code(call the function with the relevant arguments only, DO NOT WRITE THE FUNCTION DEFINITION) and nothing else. Make sure you call multiple actions if needed and dont forget to put their relevant arguments.Do not give any comments. strictly follow the function definitions. Again, do not define the functions, only call them with relevant arguments. Try making the answer detailed and split into paragraphs with highlighted titles."
        function_list = [
            # self.Actiontools.displayPdf,
            self.Actiontools.CreateNewChat,
            self.Actiontools.answerUser,
        ]
        for function in function_list:
            signature = inspect.signature(function)
            docstring = function.__doc__
            prompt += f'''
            Function:
            def self.Actiontools.{function.__name__}{signature}
                """
                {docstring.strip()}
                """
            '''
        return prompt

    def generateGraph(self):
        graph = StateGraph(AgentState)
        graph.add_node("AnswerGenerator", self.generateAnswers)
        graph.add_node("Retreiver", self.retrieveData)
        graph.add_node("websiteActions", self.websiteActions)

        # Conditional edges
        graph.add_conditional_edges(
            "AnswerGenerator",
            self.should_retrieve_data,
            {True: "Retreiver", False: "websiteActions"}
        )
        graph.add_edge("Retreiver", "AnswerGenerator")
        graph.add_edge("websiteActions", END)
        graph.set_entry_point("AnswerGenerator")
        self.graph = graph.compile()

    def should_retrieve_data(self, state: AgentState) -> bool:
        return self.AllowRequests and self.RequestData and state['iteration_count'] < 2  

    # def generateAnswers(self, state: AgentState) -> AgentState:
    #     print(state['task'])
    #     retrieved_text= self.RAGHandler.query(state['task'])
    #     combined_content = f"context: {retrieved_text}\n"
    #     print(" "*30,combined_content)
    #     response = self.model.with_structured_output(Answer).invoke([
    #         SystemMessage(content=self.AnswerGeneratorPrompt),
    #         HumanMessage(content=state['task']),
    #         HumanMessage(content=combined_content),
    #     ])
        
    #     self.answer = response.answer
    #     self.RequestData = len(response.required_info) > 0
    #     print("Requested data:",self.RequestData,response.required_info)
    #     return {
    #         'generated_answer': response.answer,
    #         'required_info': response.required_info,
    #         'iteration_count': state['iteration_count'] + 1
    #     }

    def generateAnswers(self, state: dict) -> dict:
        retrieved_text = self.RAGHandler.query(state['task'])
        print("Question:",state['task'])
        combined_content = f"context: {retrieved_text}\n"
        prompt = f"""
        User Question: {state['task']} \n
        {combined_content}\n
        instructions: {self.AnswerGeneratorPrompt}
        """

        response = ollama.generate(model=self.model, prompt=prompt)['response']
        # parsed_response = self.parse_structured_output(response)
        # print("parsed response:",parsed_response)
        self.answer = response
        self.RequestData = False
        # print("Requested data:", self.RequestData, parsed_response['required_info'])
        return {
            'generated_answer': response,
            'required_info': [],#parsed_response['required_info'],
            'iteration_count': state['iteration_count'] + 1
        }

    # def parse_structured_output(self, text: str) -> dict:
    #     lines = text.split('\n')
    #     answer = ""
    #     required_info = []
    #     for line in lines:
    #         if line.startswith("Answer: "):
    #             answer = line[7:].strip()
    #         elif line.startswith("Required Info: "):
    #             required_info = line[14:].strip().split(', ')
    #     return {"answer": answer, "required_info": required_info}

    def retrieveData(self, state: AgentState) -> AgentState:
        retreivedURL = {}
        retreivedSummary = {}
        for query in state['required_info']:
            urls, titles,summaries = self.RAGHandler.get_arxiv_pdf_url(query)
            for n, url in enumerate(urls):
                self.RAGHandler.index_pdf(url)
                retreivedURL[titles[n]] = url                
                retreivedSummary[titles[n]] = summaries[n]
        return {'retrieved_URLs': retreivedURL,'retreivedSummary': retreivedSummary}

    def websiteActions(self, state: AgentState) -> AgentState:
        prompt = f"""
        System: {self.websiteActionPrompt}
        Human Question: {state['task']}
        Answer to return to user: {state['generated_answer']}
        """

        
        self.history += "Answer: " + state['generated_answer'] + "\n"
        actions = ollama.generate(model=self.model, prompt=prompt)['response']
        self.actions = actions
        print("Returning Actions:",self.actions)
        return {'actions': actions}

    def __call__(self, prompt: str):
        self.prompt = prompt
        self.history+="Question: "+prompt + "\n"
        thread = {"configurable": {"thread_id": "1"}}
        initial_state: AgentState = {
            'task': prompt,
            'research_plan': '',
            'retrieved_URLs': {},
            'generated_answer': '',
            'actions': [],
            'required_info': [],
            'retreivedSummary':[],
            'iteration_count': 0
        }
        for s in self.graph.stream(initial_state, thread):
            pass
        self.actions = self.actions.replace("python","")
        self.actions = self.actions.replace("```","")
        try:
            exec(self.actions)
        except Exception as e:
            print(f"Error executing actions: {e}")
        return self.getActions()