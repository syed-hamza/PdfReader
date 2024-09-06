import os
from PIL import Image
from transformers import AutoTokenizer, AutoProcessor, AutoModelForZeroShotImageClassification
from qdrant_client import QdrantClient
from qdrant_client.http import models
from tqdm import tqdm
import numpy as np
import torch 

class imageHandler:
    def __init__(self,client,model_name = "openai/clip-vit-base-patch32"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.processor = AutoProcessor.from_pretrained(model_name)
        self.model = AutoModelForZeroShotImageClassification.from_pretrained(model_name)
        self.client = client
        self.collectionName = "ResearchPaperImages"
        self.client.create_collection(
            collection_name=self.collectionName,
            vectors_config=models.VectorParams(size=512, distance=models.Distance.COSINE),

        )
        pass

    def indexImageDir(self,dir):
        image_dataset = []
        for file in os.listdir(dir):
            image_path = os.path.join(dir, file)
            try:
                image = Image.open(image_path) 
                image_dataset.append(image) 
            except Exception as e:
                print(f"[INFO] Error loading image {image_path}: {e}")
        records =[]
        for idx, sample in tqdm(enumerate(image_dataset), total=len(image_dataset)):
            processed_img = self.processor(text=None, images = sample, return_tensors="pt")['pixel_values']
            img_embds = self.model.get_image_features(processed_img).detach().numpy().tolist()[0]
            img_px = list(sample.getdata())
            img_size = sample.size 
            records.append(models.Record(id=idx, vector=img_embds, payload={"pixel_lst":img_px, "img_size": img_size}))

        print("[INFO] Uploading data records to data collection...")
        for i in range(5,len(records), 5):
            self.client.upload_records(
                collection_name=self.collectionName,
                records=records[i-5:i],
            )

    def processRequest(self, text, image=None):
        if image is not None:
            # Process both text and image
            inputs = self.processor(text=text, images=image, return_tensors="pt", padding=True)
            outputs = self.model(**inputs)
            embeddings = outputs.image_embeds.detach().numpy().tolist()[0]
        else:
            # Process text only
            inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True)
            with torch.no_grad():
                text_features = self.model.text_model(**inputs).pooler_output
            text_features = self.model.text_projection(text_features)
            embeddings = text_features.detach().numpy().tolist()[0]

        hits = self.client.search(
            collection_name=self.collectionName,
            query_vector=embeddings,
            limit=5,
        )

        images = []
        for hit in hits:
            img_size = tuple(hit.payload['img_size'])
            pixel_lst = hit.payload['pixel_lst']
            new_image = Image.new("RGB", img_size)
            new_image.putdata(list(map(lambda x: tuple(x), pixel_lst)))
            images.append(new_image)
        
        return images
    
    
    # def processRequest(self,text,image = None):
    #     processed_img = self.processor(text=text, images = image, return_tensors="pt")['pixel_values']
    #     print(processed_img.keys())
        
    #     img_embeddings = self.model.get_image_features(processed_img).detach().numpy().tolist()[0]
    #     hits = self.client.search(
    #         collection_name=self.collectionName,
    #         query_vector=img_embeddings,
    #         limit=5,
    #     )

    #     images = []
    #     for hit in hits:
    #         img_size = tuple(hit.payload['img_size'])
    #         pixel_lst = hit.payload['pixel_lst']

    #         # Create an image from pixel data
    #         new_image = Image.new("RGB", img_size)
    #         new_image.putdata(list(map(lambda x: tuple(x), pixel_lst)))
    #         images.append(new_image)

    #     return images