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
        self.collections = self.qdrant_client.get_collections()
        # if self.collectionName not in [c.name for c in self.collections.collections]:
        #     self.qdrant_client.create_collection(
        #         collection_name=self.collectionName,
        #         vectors_config=VectorParams(size=512, distance=Distance.COSINE),
        #     )
        # if self.imageCollectionName not in [c.name for c in self.collections.collections]:
        #     self.qdrant_client.create_collection(
        #         collection_name=self.imageCollectionName,
        #         vectors_config=VectorParams(size=512, distance=Distance.COSINE),
        #     )
        
        self.limit = 10
        self.pdfData = {}

    def createCollection(self,pdfName):
        colName = f"{pdfName}_{self.collectionName}"
        imgColName = f"{pdfName}_{self.imageCollectionName}"
        self.collections = self.qdrant_client.get_collections()
        if colName not in [c.name for c in self.collections.collections]:
            self.qdrant_client.create_collection(
                collection_name=colName,
                vectors_config=VectorParams(size=512, distance=Distance.COSINE),
            )
        
        if imgColName not in [c.name for c in self.collections.collections]:
            self.qdrant_client.create_collection(
                collection_name=imgColName,
                vectors_config=VectorParams(size=512, distance=Distance.COSINE),
            )
        return colName,imgColName
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

    def getClientResult(self, query,pdfName, collection = None):
        if collection is None:
            collection = self.collectionName
        colName = f"{Path(pdfName).stem}_{collection}"
        query_vector = self.get_clip_embedding(text=query)
        search_result = self.qdrant_client.search(
            collection_name=colName,
            query_vector=query_vector,
            limit=self.limit
        )
        return search_result

    

    def indexAllpdf(self):
        for filename in os.listdir(self.pdfDir):
            if filename.endswith(".pdf"):
                saved = self.fileHandler.loadJSON(filename, "retreivedData")
                if not saved:
                    self.indexpdf(os.path.join(self.pdfDir, filename))
                    
    def PILImagePreprocess(self,PILImage):
            new_width, new_height = 200, 200
            pil_image = PILImage.resize((new_width, new_height))
            image_b64 = self.convert_to_base64(pil_image)
            return image_b64

    def pushImgVectors(self, path,PDFText,colImageName):
        presc_img_path = path
        for filename in os.listdir(presc_img_path):
            img_path = os.path.join(presc_img_path, filename)
            pil_image = Image.open(img_path)
            image_b64= self.PILImagePreprocess(pil_image)
            data,imgNum = self.getFigureData(PDFText,filename)
            vector = self.get_clip_embedding(text=image_b64)
            doc_id = str(uuid.uuid4())

            self.qdrant_client.upsert(
                collection_name=colImageName,
                points=[models.PointStruct(
                    id=doc_id,
                    vector=vector,
                    payload={
                        "image_data": img_path,
                        "text": data
                    }
                )]
            )
    
    
    def getDataFromImage(self, image,pdfName):
        image_b64 = self.PILImagePreprocess(image)
        data = self.getClientResult(image_b64,collection = self.imageCollectionName,pdfName = pdfName)
        text = []
        for result in data:
                text.append(result.payload['text'])
        return text[0]
        
        
    def getFigureData(self,PDFText,filename):
        pattern = r'-\d+-(\d+)\.jpg'
        match = re.search(pattern, filename).group(1)
        ind = PDFText.find(f"Figure {match}:")
        if(ind==-1):
            return -1,-1
        ind2 = PDFText[ind:].find("\n")
        return PDFText[ind:ind+ind2],match
    
    def pushImgContextAndPath(self, path, PDFText,colName):
        presc_img_path = path
        for filename in os.listdir(presc_img_path):
            img_path = os.path.join(presc_img_path, filename)
            data,imgNum = self.getFigureData(PDFText,filename)
            if(data != -1):
                print(f"[INFO] Pushing  {data}:{img_path}")
                self.pushToStore(text = data, imagePath=img_path,contentType = "Image",collectionName = colName) #self, text, imagePath=None, table="None",contentType = "Default"
                self.pushToStore(text = f"Figure {imgNum}",seperateText=data, imagePath=img_path,contentType = "Image",collectionName = colName)


    def convert_to_base64(self, pil_image):
        buffered = BytesIO()
        pil_image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return img_str

    def pushTable(self,raw_pdf_elements,colName):
        for i in range(len(raw_pdf_elements)):
            if(raw_pdf_elements[i].category =="Table"):
                if(i>=len(raw_pdf_elements)-1):
                    continue
                texts = raw_pdf_elements[i+1].text.split("\n")
                if(raw_pdf_elements[i].metadata.text_as_html == '</table>'):
                    continue
                for text in texts:
                    if("Table" in text):
                        # print(f"[INFO] Pushing {text}:{raw_pdf_elements[i].metadata.text_as_html}")
                        self.pushToStore(text=text,contentType="Table",table = raw_pdf_elements[i].metadata.text_as_html,collectionName = colName)
                        pattern = r"Table (\d+):"
                        matches = re.findall(pattern, text)
                        if(len(matches)>0):
                            num = matches[0]
                            self.pushToStore(text = f"Table {num}",seperateText=text,contentType="Table",table = raw_pdf_elements[i].metadata.text_as_html,collectionName = colName)
                        break

    def pushTextToStore(self,raw_pdf_elements,colName):
        for i in range(len(raw_pdf_elements)):
            if(raw_pdf_elements[i].category =="CompositeElement"):
                if(len(raw_pdf_elements[i].text)>5):
                    self.pushToStore(text=raw_pdf_elements[i].text,collectionName = colName)
    
    def pushToStore(self, text,collectionName, imagePath=None, table="None",contentType = "Default", seperateText= None):
        text = text.strip()
        vector = self.get_clip_embedding(text=text)
        doc_id = str(uuid.uuid4())
        if(seperateText != None):
            text = seperateText
        try:
            self.qdrant_client.upsert(
                collection_name=collectionName,
                points=[models.PointStruct(
                    id=doc_id,
                    vector=vector,
                    payload={
                        "image_path": imagePath,
                        "text": text,
                        "table":table,
                        "type" : contentType
                    }
                )]
            )
        except:
            print("[INFO]: Failed to upsert:",text)

    def indexpdf(self, pdfPath):
        pdfBaseName = Path(pdfPath).stem
        colName, colImageName = self.createCollection(pdfBaseName)
        imageDir = os.path.join(self.output_dir, pdfBaseName)
        raw_pdf_elements = partition_pdf(
            # strategy="hi_res",
            filename=pdfPath,
            extract_images_in_pdf=True,
            infer_table_structure=True,
            chunking_strategy="by_title",
            max_characters=2000,
            new_after_n_chars=1500,
            combine_text_under_n_chars=500,
            overlap = 200,
            image_output_dir_path=imageDir,
            extract_image_block_output_dir=imageDir
        )

        pdfData = [str(data) for data in raw_pdf_elements]
        strPdfData = "./".join(pdfData)
        self.pdfData[pdfBaseName] = strPdfData
        
        self.pushTextToStore(raw_pdf_elements,colName) #composite elements
        self.pushImgContextAndPath(imageDir, strPdfData,colName) #image context and path of image
        self.pushTable(raw_pdf_elements,colName) #table context and table html
        
        saved = self.fileHandler.updateJSON(pdfPath, "retreivedData", strPdfData)
        self.pushImgVectors(imageDir,strPdfData,colImageName)

    def query(self, query,pdfname):
        print(f"[INFO] {pdfname}")
        retrieval_results = self.getClientResult(query,pdfname)
        images = []
        tables = []
        text = []
        for result in retrieval_results:
            if result.payload["type"] =="Image":
                if result.payload["image_path"] not in images:
                    images.append(result.payload["image_path"])
            if result.payload["type"] =="Table":
                if [result.payload['text'],result.payload["table"]] not in images:
                    print(f"[INFO] Retreiving table: {result.payload['text']},{result.payload['table']}")
                    tables.append([result.payload['text'],result.payload["table"]])
            
            text.append(result.payload['text'])
        strtext = "./".join(text)

        return {"text": strtext, "images": images,"tables":tables}

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