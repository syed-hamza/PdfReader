import os
import requests
import io
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.llms import OpenAI
import arxiv

class RAGHandler:
    def __init__(self, index_dir="faiss_index"):
        self.index_dir = index_dir
        self.embeddings = OpenAIEmbeddings()
        if os.path.exists(index_dir):
            self.vector_store = FAISS.load_local(index_dir, self.embeddings, allow_dangerous_deserialization=True)
        else:
            self.vector_store = None

    # Step 1: Download the PDF
    def download_pdf(self, url):
        response = requests.get(url)
        return io.BytesIO(response.content)

    # Step 2: Extract text from the PDF
    def extract_text(self, pdf_file):
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text

    # Step 3: Split the text into chunks
    def split_text(self, text):
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        chunks = text_splitter.split_text(text)
        return chunks

    # Step 4 & 5: Create embeddings and store in vector database
    def update_vector_store(self, chunks):
        if self.vector_store is None:
            self.vector_store = FAISS.from_texts(chunks, self.embeddings)
        else:
            self.vector_store.add_texts(chunks)
        self.vector_store.save_local(self.index_dir)

    # Step 6: Implement query retrieval system
    def create_qa_chain(self):
        llm = OpenAI()
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=self.vector_store.as_retriever()
        )
        return qa_chain

    # Index a new PDF
    def index_pdf(self, arxiv_url):
        pdf_file = self.download_pdf(arxiv_url)
        text = self.extract_text(pdf_file)
        chunks = self.split_text(text)
        self.update_vector_store(chunks)

    # Query the indexed documents
    def query(self, question):
        if self.vector_store is None:
            return "No documents have been indexed yet."
        qa_chain = self.create_qa_chain()
        return qa_chain.run(question)
    
    def get_arxiv_pdf_url(self,query):
        search = arxiv.Search(
            query = query,
            max_results = 1,
            sort_by = arxiv.SortCriterion.Relevance
        )

        # Get the first result
        results = []
        titles = []
        summaries = []
        for result in search.results():
            results.append(result.pdf_url)
            titles.append(result.title)
            summaries.append(result.summary)
        print("results:",results)
        return results,titles,summaries
