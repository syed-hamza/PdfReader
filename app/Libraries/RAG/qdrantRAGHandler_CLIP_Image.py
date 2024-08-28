import os
import requests
from urllib.parse import unquote
import arxiv
import base64
from io import BytesIO
from qdrant_client.http import models
from typing import Any
from unstructured.partition.pdf import partition_pdf
import uuid
import fitz  # PyMuPDF
from PIL import Image
from pathlib import Path
from langchain_ollama import OllamaLLM
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from sentence_transformers import SentenceTransformer

class RAGHandler:
    def __init__(self):
        self.output_dir = "./static/Retrievedimages/"
        self.pdfDir = './papers/'
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Use a local directory for Qdrant storage
        self.qdrant_path = "./qdrant_local_storage"
        os.makedirs(self.qdrant_path, exist_ok=True)
        
        self.qdrant_client = QdrantClient(path=self.qdrant_path)
        self.collectionName = "pdfData"
        
        # Check if collection exists, create if it doesn't
        collections = self.qdrant_client.get_collections()
        if self.collectionName not in [c.name for c in collections.collections]:
            self.qdrant_client.create_collection(
                collection_name=self.collectionName,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )
        
        self.limit = 20
        self.llavallm = OllamaLLM(model="llava:latest")
        self.pdfData = {}

    def getClientResult(self, query):
        query_vector = self.embedding_model.encode(query).tolist()
        search_result = self.qdrant_client.search(
            collection_name=self.collectionName,
            query_vector=query_vector,
            limit=self.limit
        )
        return search_result

    def pushToStore(self, text, encoded_image=None):
        summary_vector = self.embedding_model.encode(text).tolist()
        doc_id = str(uuid.uuid4())

        self.qdrant_client.upsert(
            collection_name=self.collectionName,
            points=[models.PointStruct(
                id=doc_id,
                vector=summary_vector,
                payload={
                    "image_data": encoded_image,
                    "text": text
                }
            )]
        )

    def indexAllpdf(self):
        for filename in os.listdir(self.pdfDir):
            if filename.endswith(".pdf"):
                saved = self.fileHandler.loadJSON(filename, "retreivedData")
                if not saved:
                    data = self.indexpdf(os.path.join(self.pdfDir, filename))
                    saved = self.fileHandler.updateJSON(filename, "retreivedData", data)

    def getImgSummaries(self, path, context):
        cleaned_img_summary = []
        presc_img_path = path
        prompt = f"Describe the image of a research paper in detail with respect to the following context from the paper {context}. Be specific about graphs, such as bar plots."
        for filename in os.listdir(presc_img_path):
            img_path = os.path.join(presc_img_path, filename)
            print(f"Img= {img_path}")
            pil_image = Image.open(img_path)
            image_b64 = self.convert_to_base64(pil_image)
            llm_with_image_context = self.llavallm.bind(images=[image_b64])
            response = llm_with_image_context.invoke(prompt)
            cleaned_img_summary.append([response, image_b64])
        return cleaned_img_summary

    def convert_to_base64(self, pil_image):
        buffered = BytesIO()
        pil_image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return img_str

    def indexpdf(self, pdfPath):
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

        pdfData = [str(data) for data in raw_pdf_elements]
        strPdfData = "./".join(pdfData)
        self.pdfData[pdfBaseName] = strPdfData

        # Text + table
        for element in enumerate(pdfData):
            self.pushToStore(str(element))
        
        # Image
        cleaned_img_summary = self.getImgSummaries(imageDir, strPdfData)
        for summary, img in cleaned_img_summary:
            self.pushToStore(summary, img)
        return pdfData

    def query(self, query):
        retrieval_results = self.getClientResult(query)
        images = []
        text = []
        for result in retrieval_results:
            if result.payload["image_data"] is not None:
                images.append(result.payload["image_data"])
            else:
                text.append(result.payload['text'])
        return {"text": text, "images": images}

    def postProcess(self, filePath):
        self.indexpdf(filePath)

    def setFileHandler(self, fileHandler):
        self.fileHandler = fileHandler
        self.indexAllpdf()