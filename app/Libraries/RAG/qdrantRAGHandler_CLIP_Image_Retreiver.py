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
from langchain_ollama import OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain.chains import RetrievalQA
from langchain_ollama.llms import OllamaLLM
from langchain.agents import AgentType, Tool, initialize_agent
from langchain_core.documents import Document
from uuid import uuid4


class RAGHandler:
    def __init__(self):
        self.output_dir = "./static/Retrievedimages/"
        self.pdfDir = './papers/'
        
        # Initialize CLIP model and processor
        self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        self.embeddings = OllamaEmbeddings(
            model="snowflake-arctic-embed",
        )
                
        # Use a local directory for Qdrant storage
        self.qdrant_path = "./qdrant_local_storage"
        if(os.path.exists(self.qdrant_path)):
            shutil.rmtree(self.qdrant_path)
        os.makedirs(self.qdrant_path, exist_ok=True)
        
        self.qdrant_client = QdrantClient(path=self.qdrant_path)
        self.collectionName = "pdfText"
        self.collectionTableName = "pdfTable"
        self.collectionImageName = "pdfImage"
        self.imageOnlyCollectionName = "pdfImageData"
        self.collections = self.qdrant_client.get_collections()
        
        self.retreivers = {}
        self.vectorStores = {}
        self.limit = 10
        self.pdfData = {}
        
        self.model = OllamaLLM(base_url= "http://ollama:11434", model="phi3-128k:latest")

    def createCollection(self, name, collections, size = 1024, embeddings = None, retreiver = True):
        if(embeddings == None):
            embeddings = self.embeddings
        if name not in collections:
            self.qdrant_client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=size, distance=Distance.COSINE)
            )
            if retreiver:
                self.vectorStores[name] = QdrantVectorStore(
                        client=self.qdrant_client,
                        collection_name=name,
                        embedding=embeddings,
                )
                self.retreivers[name] = RetrievalQA.from_chain_type(
                    llm=self.model, chain_type="stuff", retriever=self.vectorStores[name].as_retriever()
                )

    def getTools(self,pdfName):
        if(pdfName.endswith(".pdf")):
            pdfName = Path(pdfName).stem
        colName = f"{pdfName}_{self.collectionName}"
        colTableName = f"{pdfName}_{self.collectionTableName}"
        colImageName = f"{pdfName}_{self.collectionImageName}"
        print("Invoking:")
        # print("[INFO] Retreiver test",self.retreivers[colName].invoke("Attention"))
        tools = [
            Tool(
                name="Research Paper Texts",
                func=self.retreivers[colName].invoke,
                description="Useful for when you need to answer questions about the paper in text. Input should be a Specific Keywords.",
                return_direct=True,
            ),
            Tool(
                name="Research Paper Tables",
                func=self.retreivers[colTableName].invoke,
                description="useful for when you need to get tables present in the paper. Input should be a Table number or table description.",
                return_direct=True,
            ),
            Tool(
                name="Research Paper Image Paths",
                func=self.retreivers[colImageName].invoke,
                description="useful for when you need to retreive images from the paper. Input should be a the Figure number or figure description.",
                return_direct=True,
            ),            
        ]
        return tools
        
    def createCollections(self,pdfName):
        colName = f"{pdfName}_{self.collectionName}"
        colTableName = f"{pdfName}_{self.collectionTableName}"
        colImageName = f"{pdfName}_{self.collectionImageName}"
        imgColName = f"{pdfName}_{self.imageOnlyCollectionName}"
        self.collections = self.qdrant_client.get_collections()
        collectionNames = [c.name for c in self.collections.collections]
        self.createCollection(colName,collectionNames)
        self.createCollection(colTableName,collectionNames)
        self.createCollection(colImageName,collectionNames)
        self.createCollection(imgColName,collectionNames, size = 512,retreiver= False)

        return colName,colTableName,colImageName,imgColName
    
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
        
    def get_ollama_embedding(self, text):
        return self.embeddings.embed_query(text)

    

    def indexAllpdf(self):
        for filename in os.listdir(self.pdfDir):
            if filename.endswith(".pdf"):
                saved = self.fileHandler.loadJSON(filename, "retreivedData")
                if not saved:
                    self.indexpdf(os.path.join(self.pdfDir, filename))
                    
    def PILImagePreprocess(self,PILImage):
            new_width, new_height = 200, 200
            pil_image = PILImage.resize((new_width, new_height))
            return pil_image

    def pushImgVectors(self, path,PDFText,colImageName):
        presc_img_path = path
        for filename in os.listdir(presc_img_path):
            img_path = os.path.join(presc_img_path, filename)
            pil_image = Image.open(img_path)
            # image_b64= self.PILImagePreprocess(pil_image)
            data,imgNum = self.getFigureData(PDFText,filename)
            vector = self.get_clip_embedding(image=pil_image)
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
        imagePIL = self.PILImagePreprocess(image)
        data = self.getClientResult(imagePIL,collection = self.imageOnlyCollectionName,pdfName = pdfName, Embedding=self.get_clip_embedding)
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
    
    def convert_to_base64(self, pil_image):
        buffered = BytesIO()
        pil_image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return img_str
    
    def pushImgContextAndPath(self, path, PDFText,colName):
        presc_img_path = path
        docs = []
        for filename in os.listdir(presc_img_path):
            img_path = os.path.join(presc_img_path, filename)
            data,imgNum = self.getFigureData(PDFText,filename)
            if(data != -1):
                print(f"[INFO] Pushing  {data}:{img_path}")
                docs.append(Document(
                            page_content=img_path,
                            metadata={"Figure Context": data},
                        ))
        uuids = [str(uuid4()) for _ in range(len(docs))]
        self.vectorStores[colName].add_documents(documents=docs, ids=uuids)   
        self.retreivers[colName] = RetrievalQA.from_chain_type(
            llm=self.model, chain_type="stuff", retriever=self.vectorStores[colName].as_retriever()
        )            
            

    def pushTable(self,raw_pdf_elements,colName):
        docs = []
        for i in range(len(raw_pdf_elements)):
            if(raw_pdf_elements[i].category =="Table"):
                if(i>=len(raw_pdf_elements)-1):
                    continue
                texts = raw_pdf_elements[i+1].text.split("\n")
                if(raw_pdf_elements[i].metadata.text_as_html == '</table>'):
                    continue
                for text in texts:
                    if("Table" in text):
                        docs.append(Document(
                            page_content=raw_pdf_elements[i].metadata.text_as_html,
                            metadata={"Context": text},
                        ))

                        pattern = r"Table (\d+):"
                        matches = re.findall(pattern, text)

                        if(len(matches)>0):
                            num = matches[0]
                            docs.append(Document(
                                page_content=raw_pdf_elements[i].metadata.text_as_html,
                                metadata={"Context": f"Table {num}"},
                            ))

                        break
        uuids = [str(uuid4()) for _ in range(len(docs))]
        self.vectorStores[colName].add_documents(documents=docs, ids=uuids)
        self.retreivers[colName] = RetrievalQA.from_chain_type(
            llm=self.model, chain_type="stuff", retriever=self.vectorStores[colName].as_retriever()
        )                     
        

        
    
    def pushTextToStore(self,raw_pdf_elements,colName):
        docs = []
        for i in range(len(raw_pdf_elements)):
            if(raw_pdf_elements[i].category =="CompositeElement"):
                if(len(raw_pdf_elements[i].text)>5):

                    docs.append(Document(
                        page_content=raw_pdf_elements[i].text,
                        metadata={"source": "Reseach Paper"},
                    ))
        uuids = [str(uuid4()) for _ in range(len(docs))]
        self.vectorStores[colName].add_documents(documents=docs, ids=uuids)
        self.retreivers[colName] = RetrievalQA.from_chain_type(
            llm=self.model, chain_type="stuff", retriever=self.vectorStores[colName].as_retriever()
        )         
    
    def pushToStore(self, text,collectionName,payload, seperateText= None):
        text = text.strip()
        vector = self.get_ollama_embedding(text=text)
        doc_id = str(uuid.uuid4())
        if(seperateText != None):
            text = seperateText
        try:
            self.qdrant_client.upsert(
                collection_name=collectionName,
                points=[models.PointStruct(
                    id=doc_id,
                    vector=vector,
                    payload=payload
                )]
            )
        except:
            print("[INFO]: Failed to upsert:",text)

    def indexpdf(self, pdfPath):
        pdfBaseName = Path(pdfPath).stem
        colName,colTableName,colImageName,imgColName = self.createCollections(pdfBaseName)
        imageDir = os.path.join(self.output_dir, pdfBaseName)
        raw_pdf_elements = partition_pdf(
            # strategy="hi_res",
            filename=pdfPath,
            extract_images_in_pdf=True,
            infer_table_structure=True,
            chunking_strategy="by_title",
            max_characters=1000,
            new_after_n_chars=600,
            combine_text_under_n_chars=400,
            overlap = 100,
            image_output_dir_path=imageDir,
            extract_image_block_output_dir=imageDir
        )

        pdfData = [str(data) for data in raw_pdf_elements]
        strPdfData = "./".join(pdfData)
        self.pdfData[pdfBaseName] = strPdfData
        
        self.pushTextToStore(raw_pdf_elements,colName) #composite elements
        self.pushImgContextAndPath(imageDir, strPdfData,colImageName) #image context and path of image
        self.pushTable(raw_pdf_elements,colTableName) #table context and table html
        
        saved = self.fileHandler.updateJSON(pdfPath, "retreivedData", strPdfData)
        self.pushImgVectors(imageDir,strPdfData,imgColName)

    
    def getClientResult(self, query,pdfName, collection = None, limit = None, Embedding = None):
        if collection is None:
            collection = self.collectionName
        if limit is None:
            limit = self.limit
        if Embedding is None:
            query_vector = self.get_ollama_embedding(text=query)
        else:
            query_vector = Embedding(image=query)
        colName = f"{Path(pdfName).stem}_{collection}"
        search_result = self.qdrant_client.search(
            collection_name=colName,
            query_vector=query_vector,
            limit=limit
        )
        return search_result

    def query(self, query,pdfname):
        print(f"[INFO] {pdfname}")
        textResults = self.getClientResult(query,pdfname)
        tableResults = self.getClientResult(query,pdfname,collection=self.collectionTableName, limit =1)
        imageResults = self.getClientResult(query,pdfname,collection=self.collectionImageName, limit =1)
        images = []
        tables = []
        text = []
        for result in textResults:
            text.append(result)
        for result in tableResults:
            tables.append(result) 
            text.append(result)
        for result in imageResults:
            images.append(result)
            text.append(result)
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