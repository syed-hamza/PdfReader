import os
import requests
from urllib.parse import unquote
import arxiv
import base64
from io import BytesIO

from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import Qdrant
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.retrievers.multi_vector import MultiVectorRetriever
from langchain.storage import InMemoryStore
from typing import Any
from pydantic import BaseModel
from unstructured.partition.pdf import partition_pdf
import uuid
from langchain_core.documents import Document
import fitz  # PyMuPDF
from PIL import Image
from pathlib import Path
from langchain_ollama import OllamaLLM
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from Libraries.clipImageHandler import imageHandler

class RAGHandler:
    def __init__(self):
        self.output_dir = "./static/Retrievedimages/"
        self.pdfDir = './papers/'
        self.index = None
        self.embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        self.qdrant_client = QdrantClient("qdrant_store") 

        self.qdrant_client.create_collection(
            collection_name="qdrant_store",
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )
        self.imageHandler = imageHandler(self.qdrant_client)
        # Initialize Qdrant vector store
        self.vector_store = Qdrant(
            client=self.qdrant_client,
            collection_name="qdrant_store",
            embeddings=self.embedding_model,
        )
        
        store = InMemoryStore()
        id_key = "doc_id"
        self.retriever = MultiVectorRetriever(
            vectorstore=self.vector_store,
            docstore=store,
            id_key=id_key,
        )
        self.llavallm = OllamaLLM(model="llava:latest")
        self.pdfData = {}


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

    def getAllPdfText(self,pdfName):
        pdfName = Path(pdfName).stem
        if pdfName in self.pdfData.keys():
            return self.pdfData[pdfName]
        else:
            path = os.path.join(self.pdfDir,pdfName+".pdf")
            self.indexpdf(path)
            return self.pdfData[pdfName]


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
    def indexAllpdf(self, arxiv_url = None):
        if(arxiv_url != None):
            path = self.download_pdf(arxiv_url)
            self.pdf_to_images(path)
        documents = []
        for filename in os.listdir(self.pdfDir):
            if filename.endswith(".pdf"):
                saved = self.fileHandler.loadJSON(filename,"retreivedData")
                print("saved:",saved)
                if saved==[]:
                    data = self.indexpdf(os.path.join(self.pdfDir,filename))
                    saved = self.fileHandler.updateJSON(filename,"retreivedData",data)
                

    def getImgSummaries(self,path):
        cleaned_img_summary = []
        presc_img_path=path
        prompt="Describe the image in detail. Be specific about graphs, such as bar plots."
        for filename in os.listdir(presc_img_path)[:5]: 
            presc_file_path =presc_img_path+filename
            img_path = os.path.join(presc_img_path, filename) 
            basename = Path(filename).stem
            if os.path.isfile(img_path):
                print("Img= {}".format(img_path))
                pil_image = Image.open(img_path)
                image_b64 = self.convert_to_base64(pil_image)
                llm_with_image_context = self.llavallm.bind(images=[image_b64])
                response = llm_with_image_context.invoke(prompt)
                cleaned_img_summary.append(response)
        return cleaned_img_summary

    def convert_to_base64(self,pil_image):
        buffered = BytesIO()
        #pil_image.save(buffered, format="JPEG")  # You can change the format if needed
        pil_image.save(buffered, format="PNG")  # You can change the format if needed
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return img_str
    

    def indexpdf(self, pdfPath):
        id_key = "doc_id"
        pdfBaseName = Path(pdfPath).stem
        imageDir = os.path.join(self.output_dir, pdfBaseName)
        raw_pdf_elements = partition_pdf(
            filename=pdfPath,
            extract_images_in_pdf=True,
            infer_table_structure=True,
            chunking_strategy="by_title",
            max_characters=4000,
            new_after_n_chars=3800,
            combine_text_under_n_chars=2000,
            image_output_dir_path=imageDir,
            extract_image_block_output_dir=imageDir
        )

        doc_ids = [str(uuid.uuid4()) for _ in raw_pdf_elements]
        summary_texts = [
            Document(page_content=str(s), metadata={id_key: doc_ids[i]})
            for i, s in enumerate(raw_pdf_elements)
        ]
        
        # Add documents to Qdrant
        self.vector_store.add_documents(summary_texts)
        self.retriever.docstore.mset(list(zip(doc_ids, raw_pdf_elements)))

        self.imageHandler.indexImageDir(imageDir)

        # cleaned_img_summary = self.getImgSummaries(imageDir)
        # img_ids = [str(uuid.uuid4()) for _ in cleaned_img_summary]
        # summary_img = [
        #     Document(page_content=s, metadata={id_key: img_ids[i]})
        #     for i, s in enumerate(cleaned_img_summary)
        # ]
        
        # # Add image summaries to Qdrant
        # self.vector_store.add_documents(summary_img)
        # self.retriever.docstore.mset(list(zip(img_ids, cleaned_img_summary)))

        pdfData = [str(data) for data in raw_pdf_elements]
        strPdfData = "./".join(pdfData)
        self.pdfData[pdfBaseName] = strPdfData
        return pdfData

    def query(self, query):
        # Use Qdrant's similarity search
        retrieval_results = self.vector_store.similarity_search(query)
        combined_results = "\n\n".join([str(result) for result in retrieval_results])
        images = self.imageHandler.processRequest(text = query)
        return {"text":combined_results,"images":images}

    def postProcess(self,filePath):
        # self.pdf_to_images(filePath)
        self.indexpdf(filePath)

    def setFileHandler(self,fileHandler):
        self.fileHandler = fileHandler
        self.indexAllpdf()