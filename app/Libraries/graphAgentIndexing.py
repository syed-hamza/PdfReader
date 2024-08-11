
from typing import TypedDict, Annotated, List
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

# from Libraries.RAGHandler import RAGHandler

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
        self.AnswerGeneratorPrompt = """You are a senior Librarian tasked with answering questions and identifying areas where more information is needed. Based on the user's question and any retrieved content, provide an answer and list any topics or questions that require further research, Use only the context provided, not your own knowledge. Make sure you list topics if the context doesnt show relevant information.

Your response should be structured as follows:
1. Answer: Provide a concise answer to the user's question based on available information, if the user asks to display any paper put the topic in the requiredinfo.make sure you use the context for relevant information and not make your own.
2. Required Info: If a person requests any research paper(like display or show) this list should include the title of the paper.

Remember to be informative, accurate, and identify gaps in knowledge when necessary. If you dont have the information, just put in the required info please."""

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
        return self.answer
    
    def getUserQuery(self):
        return self.prompt
    
    def getActions(self):
        return self.Actiontools.returnActions()

    def getWebsiteActionPrompt(self):
        prompt = "Here are the functions to call to change the users view, write the string form of python code to call the function appropriately based on what actions are required to satisfy the user based on his question and the answer, make sure its directly executable as i will run the exec function  and no error should be raised.Only return the code and nothing else. make sure you call multiple actions if needed and dont forget to put their relevant arguments."
        function_list = [
            self.Actiontools.displayPdf,
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

    def generateAnswers(self, state: AgentState) -> AgentState:
        # Query the already indexed documents
        print(state['task'])
        retrieved_text= self.RAGHandler.query(state['task'])
        # Combine the retrieved text with any previously retrieved content
        combined_content = f"context: {retrieved_text}\n"
        print(" "*30,combined_content)
        response = self.model.with_structured_output(Answer).invoke([
            SystemMessage(content=self.AnswerGeneratorPrompt),
            HumanMessage(content=state['task']),
            HumanMessage(content=combined_content),
            # HumanMessage(content="The following is the history of the conversation:\n"+self.history),
        ])
        
        self.answer = response.answer
        self.RequestData = len(response.required_info) > 0
        print("Requested data:",self.RequestData,response.required_info)
        return {
            'generated_answer': response.answer,
            'required_info': response.required_info,
            'iteration_count': state['iteration_count'] + 1
        }

    def retrieveData(self, state: AgentState) -> AgentState:
        retreivedURL = {}
        retreivedSummary = {}
        for query in state['required_info']:
            urls, titles,summaries = self.RAGHandler.get_arxiv_pdf_url(query)
            for n, url in enumerate(urls):
                self.RAGHandler.index_pdf(url)
                retreivedURL[titles[n]] = url                
                retreivedSummary[titles[n]] = summaries[n]
        # We're not querying here anymore, just indexing new documents
        return {'retrieved_URLs': retreivedURL,'retreivedSummary': retreivedSummary}

    def websiteActions(self, state: AgentState) -> AgentState:
        messages = [
            HumanMessage(content=state['task']),
            HumanMessage(content=f"Retrieved PDF URLs: {json.dumps(state['retrieved_URLs'], indent=2)}."),
            HumanMessage(content=state['generated_answer']),
            SystemMessage(content=self.websiteActionPrompt)
        ]
        self.history += "Answer: " + state['generated_answer'] + "\n"
        actions = self.model.invoke(messages)
        self.actions = actions
        print("Returning Actions:",self.actions)
        return {'actions': str(actions)}

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
        self.actions = self.actions.content.replace("python","")
        self.actions = self.actions.replace("```","")
        try:
            exec(self.actions)
        except Exception as e:
            print(f"Error executing actions: {e}")
        return self.getActions()