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


class RAGHandler:
    def __init__(self,client):
        print("_"*10 + "creating qdrant"+"_"*10)
        self.output_dir = "./static/images/"
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
        
        # Send a GET request with stream=True to handle large files
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Get the filename from the Content-Disposition header if available
        content_disposition = response.headers.get('Content-Disposition')
        if content_disposition:
            filename = content_disposition.split('filename=')[1].strip('"')
        else:
            # If Content-Disposition is not available, use the URL's filename
            filename = unquote(os.path.basename(url))
        
        # Ensure the filename ends with .pdf
        if not filename.lower().endswith('.pdf'):
            filename += '.pdf'
        
        path = os.path.join(self.pdfDir, filename)
        
        # Save the PDF file in chunks
        with open(path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        print(f"PDF downloaded and saved as: {filename}")
        
        return path


    def extract_images(self, pdf_path, output_dir):
        name = os.path.basename(pdf_path)
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images(full=True)
            
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                
                # Get image extension
                ext = base_image["ext"]
                
                # Save image
                image = Image.open(io.BytesIO(image_bytes))
                image.save(os.path.join(output_dir, f'{name}_image_page{page_num + 1}_{img_index + 1}.{ext}'))


    # Index a new PDF
    def index_pdf(self, arxiv_url = None):
        if(arxiv_url != None):
            path = self.download_pdf(arxiv_url)
            self.extract_images(path,self.output_dir)
        try:
            documents1 = SimpleDirectoryReader(self.pdfDir).load_data()
            documents2 = SimpleDirectoryReader(self.output_dir).load_data()
            documents = documents1 + documents2
            self.index = MultiModalVectorStoreIndex.from_documents(
                documents,
                storage_context=self.storage_context,
            )
        except:
            self.index = None

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
        
        return retrieved_text, retrieved_images
    
    def get_arxiv_pdf_url(self,query):
        search = arxiv.Search(
            query = query,
            max_results = 3,
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
