import os
import requests
import io
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from urllib.parse import unquote

import arxiv


from llama_index.core import SimpleDirectoryReader
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.indices import MultiModalVectorStoreIndex
import fitz  # PyMuPDF
from PIL import Image
import os
from llama_index.core.schema import ImageNode
from pathlib import Path


class RAGHandler:
    def __init__(self,client):
        self.output_dir = "./static/Retrievedimages/"
        self.pdfDir = './papers/'
        self.index_dir = "qdrant_index"
        self.embeddings = OpenAIEmbeddings()
        self.llm = ChatOpenAI(model="gpt-4")
        self.client = client
        text_store = QdrantVectorStore(
                client=self.client, collection_name="text_collection_app"
            )
        image_store = QdrantVectorStore(
            client=self.client, collection_name="image_collection_app"
        )
        self.storage_context = StorageContext.from_defaults(
            vector_store=text_store, image_store=image_store
        )
        self.index_pdf()


    def download_pdf(self, url):
        print(f"Downloading PDF from {url}")
    
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Get the filename from the Content-Disposition header if available
        content_disposition = response.headers.get('Content-Disposition')
        if content_disposition:
            filename = content_disposition.split('filename=')[1].strip('"')
        else:
            filename = unquote(os.path.basename(url))
        
        if not filename.lower().endswith('.pdf'):
            filename += '.pdf'
        
        path = os.path.join(self.pdfDir, filename)
        with open(path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        print(f"PDF downloaded and saved as: {filename}")
        
        return path

    def pdf_to_images(self,pdf_path):
        pdf_document = fitz.open(pdf_path)
        pdf_name = Path(pdf_path).stem
        path = os.path.join(self.output_dir,pdf_name)
        if not os.path.exists(path):
            os.makedirs(path)
        for page_num in range(pdf_document.page_count):
            page = pdf_document.load_page(page_num)
            pix = page.get_pixmap()
            output_image_path = os.path.join(path,f"{page_num + 1}.png")
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img.save(output_image_path)


    # Index a new PDF
    def index_pdf(self, arxiv_url = None):
        if(arxiv_url != None):
            path = self.download_pdf(arxiv_url)
            self.pdf_to_images(path)
        try:
            documents = SimpleDirectoryReader(self.pdfDir).load_data()
            self.index = MultiModalVectorStoreIndex.from_documents(
                documents,
                storage_context=self.storage_context,
                )
        except:
            print("input dir empty")
            pass

    def indexSoloPdf(self, pdfPath):
        documents = SimpleDirectoryReader(pdfPath).load_data()
        PDFindex = MultiModalVectorStoreIndex.from_documents(
            documents,
            storage_context=self.storage_context,
            )
        return PDFindex

    def query(self, question):
        if self.index ==None:
            return "No information indexed, please retreive info", []
        retriever = self.index.as_retriever(similarity_top_k=3, image_similarity_top_k=5)
        retrieval_results = retriever.retrieve(question)
        retrieved_images = []
        retrieved_text = ""
        for res_node in retrieval_results:
            if isinstance(res_node.node, ImageNode):
                retrieved_images.append(res_node.node.metadata["file_path"])
            else:
                retrieved_text += res_node.get_content()
        
        return retrieved_text#, retrieved_images
    
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

    def postProcess(self,filePath):
        self.pdf_to_images(filePath)
        self.index_pdf()
