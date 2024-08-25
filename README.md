# IntelliPaper
$ git clone https://github.com/ROCmSoftwarePlatform/flash-attention.git -b howiejayz/navi_support --depth=1
$ cd flash-attention
$ export PYTHON_SITE_PACKAGES=$(python -c 'import site; print(site.getsitepackages()[0])')
$ FLASH_ATTENTION_INTERNAL_USE_RTN=1 pip install .
```
### Install Optimum-AMD for accessing Hugggingface Libraries
For installing many advanced models from HuggingFace the package Optimum-AMD is very useful:
[Find out more about these integrations in the documentation](https://huggingface.co/docs/optimum/main/en/amd/amdgpu/overview)!
```bash
$ pip install --upgrade-strategy eager optimum[amd]      
``` 

After installing PyTorch, FT2(optional), and Optimum-AMD, the system will be ready to deploy advanced models through HuggingFace and the package Ollama.  
       
### Installing Ollama:
Ollama interface can deploy  many LLMs to use in systems with AMD GPUs. The installation of Ollama can be done by running a single command: 
```bash
$ curl -fsSL https://ollama.com/install.sh | sh
```
The details of Ollama installation and the list of LLMs that can be deployed are given in the link [Ollama](https://github.com/ollama/ollama/tree/main)
       
For our work, we deployed the following models: Llama3.1 70B, Azure Phi3 medium(14B), 
The model llama3.1 (70B) is deployed in the system using the following command:
```bash       
$ ollama run llama3.1:70b
```

### Installing Whisper (medium size)
For installing the Speech-to-Text model Whisper model in ROCm6.1 we followed the instructions [ROCm Whisper]( https://rocm.blogs.amd.com/artificial-intelligence/whisper/README.html)

## Deploying IntelliPaper  

### Installing in local directory
1. Clone this repository
    ```bash
    git clone https://github.com:syed-hamza/PdfReader.git
    cd PdfReader
    ```
2. Install the required Python packages
    ```bash
    cd app
    pip install -r requirements.txt
    ```
3. Run the application
    ```bash
    python ./app.py
    ```
4. Launch the IntelliPaper dashboard
   http://127.1.1.0:5000

### Installing through Docker
IntelliPaper build can be done through Docker using the command
$ docker build -t pdfr .

The docker build command will create a container with PyTorch, Optimum-AMD, and IntelliApp code. 
The command to run the container is
$ docker run -p 5000:5000 --network="host" -it pdfr

## IntelliPaper User guide
IntelliPaper dashboard has three panels:
1) Left side panel is uploading a research paper,
2) Middle panel is for viewing the paper summary,
3) Right panel is for browsing the pdf version of the research paper.

Generate Summary button generates the summary of the entire research paper using the Llama 3.1 (70B) model deployed in Ollama framework. The generated Summary is presented in the middle panel. The Audio button presents the narrative of the research paper summary. The yellow marker moves to show the location of the text in the speech.
The middle panel also has a QnA chatbot interface. Here users can ask questions regarding the uploaded research paper. For example, user can query "What is Flash Attention 2?". This chat interface is also can be operated using voice comand. 


## Contributing
If you have any suggestions or find any issues, please create an issue or submit a pull request.

## License
This project is licensed under the MIT License. See the [LICENSE](Licence) file for details.

## Acknowledgements

Feel free to reach out if you have any questions or need further assistance!
