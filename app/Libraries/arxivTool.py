
class arxivTool():
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