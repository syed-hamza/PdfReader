import os
import base64
import re
from io import BytesIO
import io
from unstructured.partition.pdf import partition_pdf
import uuid
from PIL import Image
from pathlib import Path
import torch
import shutil
from langchain.chains import RetrievalQA
from langchain_ollama.llms import OllamaLLM
from uuid import uuid4
from langchain.vectorstores import Chroma
from langchain_experimental.open_clip import OpenCLIPEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough,RunnableParallel
from operator import itemgetter

class RAGHandler:
    def __init__(self):
        self.output_dir = "./static/Retrievedimages/"
        self.pdfDir = './papers/'
        
        # Initialize CLIP model and processor
        self.embeddings = OpenCLIPEmbeddings
                
        # Use a local directory for Qdrant storage
        # self.qdrant_path = "./qdrant_local_storage"
        # if(os.path.exists(self.qdrant_path)):
        #     shutil.rmtree(self.qdrant_path)
        # os.makedirs(self.qdrant_path, exist_ok=True)
        
        self.retreivers = {}
        self.vectorStores = {}
        self.limit = 10
        self.pdfData = {}
        
        self.model = OllamaLLM(base_url= "http://ollama:11434", model="phi3-128k:latest")
        

    def createCollection(self, name, embeddings = None):
        if(embeddings == None):
            embeddings = self.embeddings
        self.vectorStores[name] = Chroma(
            collection_name=name, embedding_function=embeddings()
        )

        
    def createCollections(self,pdfName): # if more than one is required
        self.createCollection(pdfName)
 
    def PILImagePreprocess(self,PILImage):
            new_width, new_height = 200, 200
            pil_image = PILImage.resize((new_width, new_height))
            return pil_image
        
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
            docs.append(img_path)
        self.vectorStores[colName].add_images(docs)   
                  
            

    def pushTable(self,raw_pdf_elements,colName):
        docs = []
        for i in range(len(raw_pdf_elements)):
            if(raw_pdf_elements[i].category =="Table"):
                if(i>=len(raw_pdf_elements)-1):
                    continue
                texts = raw_pdf_elements[i+1].text.split("\n")
                if(raw_pdf_elements[i].metadata.text_as_html == '</table>'):
                    continue
                docs.append(raw_pdf_elements[i].metadata.text_as_html)
        self.vectorStores[colName].add_texts(docs)        
        

        
    
    def pushTextToStore(self,raw_pdf_elements,colName):
        docs = []
        for i in range(len(raw_pdf_elements)):
            if(raw_pdf_elements[i].category =="CompositeElement"):
                if(len(raw_pdf_elements[i].text)>5):
                    docs.append(raw_pdf_elements[i].text)
        self.vectorStores[colName].add_texts(texts=docs)

    def indexpdf(self, pdfPath):
        pdfBaseName = Path(pdfPath).stem
        self.createCollections(pdfBaseName)
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
        
        self.pushTextToStore(raw_pdf_elements,pdfBaseName) #composite elements
        self.pushImgContextAndPath(imageDir, strPdfData,pdfBaseName) #image context and path of image
        self.pushTable(raw_pdf_elements,pdfBaseName) #table context and table html
        
        saved = self.fileHandler.updateJSON(pdfPath, "retreivedData", strPdfData)
        self.retreivers[pdfBaseName] = self.vectorStores[pdfBaseName].as_retriever()

    
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

    def split_image_text_types(self,docs):
        """Split numpy array images and texts"""
        images = []
        text = []
        for doc in docs:
            doc = doc.page_content  # Extract Document contents
            if self.is_base64(doc):
                images.append(
                    self.resize_base64_image(doc, size=(250, 250))
                )  # base64 encoded str
            else:
                text.append(doc)
        return {"images": images, "texts": text}

    def prompt_func(self,data_dict):
        # Joining the context texts into a single string
        formatted_texts = "\n".join(data_dict["context"]["texts"])
        messages = []

        # Adding image(s) to the messages if present
        if data_dict["context"]["images"]:
            image_message = {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{data_dict['context']['images'][0]}"
                },
            }
            messages.append(image_message)

        # Adding the text message for analysis
        text_message = {
            "type": "text",
            "text": (
                "As an Professor, your task is to analyze and interpret images, "
                "considering their historical and cultural significance. Alongside the images, you will be "
                "provided with related text to offer context. Both will be retrieved from a vectorstore based "
                "on user-input keywords. Please use your extensive knowledge and analytical skills to provide a "
                "comprehensive answer that includes:\n"
                "- A detailed description of the visual elements in the image.\n"
                f"User-provided keywords: {data_dict['question']}\n\n"
                "Text and / or tables:\n"
                f"{formatted_texts}"
            ),
        }
        messages.append(text_message)

        return [HumanMessage(content=messages)]

    def query(self, query,pdfname):
        print(f"[INFO] {pdfname}")
        pdfname = Path(pdfname).stem
        chain =(
            {
                "context": self.retreivers[pdfname] | RunnableLambda(self.split_image_text_types),
                "question": RunnablePassthrough(),
            }
            | RunnableParallel({"response":self.prompt_func| self.model| StrOutputParser(),
                            "context": itemgetter("context"),})
        )
        response = chain.invoke(query)
        print(f"[INFO] response {response}")
        return {"text": response['response'], "images": response['context']['images'],"tables":[]}

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
        # self.indexAllpdf()

    
    
    def resize_base64_image(self,base64_string, size=(128, 128)):
        """
        Resize an image encoded as a Base64 string.

        Args:
        base64_string (str): Base64 string of the original image.
        size (tuple): Desired size of the image as (width, height).

        Returns:
        str: Base64 string of the resized image.
        """
        # Decode the Base64 string
        img_data = base64.b64decode(base64_string)
        img = Image.open(io.BytesIO(img_data))

        # Resize the image
        resized_img = img.resize(size, Image.LANCZOS)

        # Save the resized image to a bytes buffer
        buffered = io.BytesIO()
        resized_img.save(buffered, format=img.format)

        # Encode the resized image to Base64
        return base64.b64encode(buffered.getvalue()).decode("utf-8")


    def is_base64(self,s):
        """Check if a string is Base64 encoded"""
        try:
            return base64.b64encode(base64.b64decode(s)) == s.encode()
        except Exception:
            return False


    