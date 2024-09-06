import os
import base64
import re
from io import BytesIO
from qdrant_client.http import models
from unstructured.partition.pdf import partition_pdf
import uuid
from PIL import Image
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
import torch
from transformers import CLIPProcessor, CLIPModel
import shutil

class RAGHandler:
    def __init__(self):
        self.output_dir = "./static/Retrievedimages/"
        self.pdfDir = './papers/'
        
        # Initialize CLIP model and processor
        self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        
        # Use a local directory for Qdrant storage
        self.qdrant_path = "./qdrant_local_storage"
        if(os.path.exists(self.qdrant_path)):
            shutil.rmtree(self.qdrant_path)
        os.makedirs(self.qdrant_path, exist_ok=True)
        
        self.qdrant_client = QdrantClient(path=self.qdrant_path)
        self.collectionName = "pdfData"
        self.imageCollectionName = "pdfImageData"
        
        # Check if collection exists, create if it doesn't
        collections = self.qdrant_client.get_collections()
        if self.collectionName not in [c.name for c in collections.collections]:
            self.qdrant_client.create_collection(
                collection_name=self.collectionName,
                vectors_config=VectorParams(size=512, distance=Distance.COSINE),
            )
        if self.imageCollectionName not in [c.name for c in collections.collections]:
            self.qdrant_client.create_collection(
                collection_name=self.imageCollectionName,
                vectors_config=VectorParams(size=512, distance=Distance.COSINE),
            )
        
        self.limit = 10
        self.pdfData = {}

    def get_clip_embedding(self, text=None, image=None):
        if text:
            inputs = self.clip_processor(text=text, return_tensors="pt", padding=True, truncation=True)
            with torch.no_grad():
                text_features = self.clip_model.get_text_features(**inputs)
            return text_features.squeeze().tolist()
        elif image:
            inputs = self.clip_processor(images=image, return_tensors="pt")
            with torch.no_grad():
                image_features = self.clip_model.get_image_features(**inputs)
            return image_features.squeeze().tolist()

    def getClientResult(self, query, collection = None):
        if collection is None:
            collection = self.collectionName
        query_vector = self.get_clip_embedding(text=query)
        search_result = self.qdrant_client.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=self.limit
        )
        return search_result

    def pushToStore(self, text, encoded_image=None):
        vector = self.get_clip_embedding(text=text)
        doc_id = str(uuid.uuid4())

        self.qdrant_client.upsert(
            collection_name=self.collectionName,
            points=[models.PointStruct(
                id=doc_id,
                vector=vector,
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
                    self.indexpdf(os.path.join(self.pdfDir, filename))
                    

    def pushImgVectors(self, path,PDFText):
        presc_img_path = path
        for filename in os.listdir(presc_img_path):
            img_path = os.path.join(presc_img_path, filename)
            print(f"Img= {img_path}")
            pil_image = Image.open(img_path)
            image_b64 = self.convert_to_base64(pil_image)
            data = self.getFigureData(PDFText,filename)
            vector = self.get_clip_embedding(text=image_b64)
            doc_id = str(uuid.uuid4())

            self.qdrant_client.upsert(
                collection_name=self.imageCollectionName,
                points=[models.PointStruct(
                    id=doc_id,
                    vector=vector,
                    payload={
                        "image_data": img_path,
                        "text": data
                    }
                )]
            )
    
    
    def getDataFromBase64Image(self, image_b64):
        data = self.getClientResult(image_b64,collection = self.imageCollectionName)
        text = []
        for result in data:
                text.append(result.payload['text'])
        return text
        
        
    def getFigureData(self,PDFText,filename):
        pattern = r'-\d+-(\d+)\.jpg'
        match = re.search(pattern, filename).group(1)
        ind = PDFText.find(f"Figure {match}:")
        if(ind==-1):
            return -1
        ind2 = PDFText[ind:].find("\n")
        return PDFText[ind:ind+ind2]
    
    def getImgData(self, path, PDFText):
        cleaned_img_summary = []
        presc_img_path = path
        for filename in os.listdir(presc_img_path):
            img_path = os.path.join(presc_img_path, filename)
            data = self.getFigureData(PDFText,filename)
            if(data != -1):
                cleaned_img_summary.append([data, img_path])
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
            # strategy="hi_res",
            filename=pdfPath,
            extract_images_in_pdf=True,
            infer_table_structure=True,
            chunking_strategy="by_title",
            max_characters=600,
            new_after_n_chars=380,
            combine_text_under_n_chars=200,
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
        cleaned_img_summary = self.getImgData(imageDir, strPdfData)
        for summary, img in cleaned_img_summary:
            self.pushToStore(summary, img)
        saved = self.fileHandler.updateJSON(pdfPath, "retreivedData", strPdfData)
        self.pushImgVectors(imageDir,strPdfData)

    def query(self, query):
        print("retreiving query")
        retrieval_results = self.getClientResult(query)
        images = []
        text = []
        for result in retrieval_results:
            if result.payload["image_data"] is not None:
                images.append(result.payload["image_data"])
            else:
                text.append(result.payload['text'])
            strtext = "./".join([eval(element)[1] for element in text])
        return {"text": strtext, "images": images}

    def postProcess(self, filePath):
        self.indexpdf(filePath)

    def getAllPdfText(self,pdfName):
        pdfName = Path(pdfName).stem
        if pdfName in self.pdfData.keys():
            return self.pdfData[pdfName]
        else:
            path = os.path.join(self.pdfDir,pdfName+".pdf")
            self.indexpdf(path)
            return self.pdfData[pdfName]

    def setFileHandler(self, fileHandler):
        self.fileHandler = fileHandler
        self.indexAllpdf()