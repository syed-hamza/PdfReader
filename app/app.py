from flask import Flask, request, jsonify, render_template, Response
import sys 
import os
import base64
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'Libraries/VideoGen')))

from Libraries.chathandler import chatHandlerClass


app = Flask(__name__)
chatHandler = chatHandlerClass()
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video')
def video():
    return render_template('video.html')

@app.route('/test/<int:number>')
def test(number):
    image_data = chatHandler.getImage(number)
    if image_data:
        # If image data is available, return it as a response
        return Response(base64.b64decode(image_data), mimetype='image/jpeg')
    else:
        # If no image is available, render the template without image data
        return render_template('index.html', image_data=None)

@app.route('/conversations', methods=['GET'])
def get_conversations():
    conversations = chatHandler.load_conversations()
    return jsonify(conversations)


@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    conversation_id = request.json.get('conversation_id')
    return chatHandler.chat(conversation_id,user_message)

@app.route('/getImage', methods=['POST'])
def getImage():
    return chatHandler.getImageHTML(0)

@app.route('/new_chat', methods=['POST'])
def new_chat():
    new_conversation = chatHandler.new_chat()
    return jsonify(new_conversation)

@app.route('/delete_chat/<int:conversation_id>', methods=['DELETE'])
def delete_chat(conversation_id):
    chatHandler.delete_chat(conversation_id)
    return '', 204

@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    if 'audio' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['audio']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file:
        conversation_id = int(request.args.get('convId'))
        return chatHandler.upload_audio(file,conversation_id)
    return jsonify({'error': 'File upload failed'}), 400

@app.route('/get-elements')
def get_elements():
    elements = chatHandler.getPdf()
    return jsonify(elements)

@app.route('/upload-pdf', methods=['POST'])
def upload_pdf():
    if 'pdf' not in request.files:
        return jsonify({'success': False, 'message': 'No file part'})
    
    file = request.files['pdf']
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file'})
    if file and file.filename.endswith('.pdf'):
        fileName = chatHandler.uploadPDF(file)
        return jsonify({'success': True, 'message': 'File uploaded successfully', 'fileName':fileName})
    
    return jsonify({'success': False, 'message': 'Invalid file type'})

@app.route('/get-pdf')
def getPdf():
    pdf_path = request.args.get('filename')
    return chatHandler.sendPDF(pdf_path)

@app.route('/isVideoGenerated')
def isVideoGenerated():
    pdf_path = request.args.get('filename')
    return chatHandler.videoFileExists(pdf_path) #returns True or False


@app.route('/getSummary')
def getSummary():
    pdfName = request.args.get('filename')
    summary = chatHandler.summarizePDFOllama(pdfName)
    return summary



@app.route('/getSubtitles')
def getSubtitles():
    pdf_path = request.args.get('pdfName')
    return chatHandler.getSubtitles(pdf_path)

@app.route('/toggleArxiv')
def ToggleArxiv():
    current = chatHandler.toggleArxiv()
    return f'archive requests set to {current}'

@app.route('/Arxivallowed')
def checkArxiv():
    return chatHandler.isArxivAllowed()

@app.route('/get_video_path', methods=['GET'])
def get_video_path():
    
    pdfName =  request.args.get('pdfName')[:-4]
    video_path = f'/static/results/{pdfName}.mp4'
    print(os.path.exists(video_path))
    return jsonify({'video_url': video_path})

# @app.route('/update_timestamp', methods=['POST'])
# def update_timestamp():
#     data = request.get_json()
#     timestamp = data['timestamp']
#     pdfname = data['pdfName']
#     image = chatHandler.retrieveRelevantPdfImage(pdfname,timestamp) #return image
#     return image

@app.route('/update_timestamp', methods=['POST'])
def update_timestamp():
    data = request.get_json()
    timestamp = data['timestamp']
    pdfname = data['pdfName']
    classname = chatHandler.retrieveRelevanclassName(pdfname,timestamp) #return image
    return classname

@app.route('/get_audio')
def serve_audio():
    pdfName =  request.args.get('pdfName')
    return chatHandler.getAudio(pdfName)

# if __name__ == '__main__':
#     app.run(ssl_context=('cert.pem', 'key.pem'),debug=True,use_reloader=False, host="0.0.0.0")

if __name__ == '__main__':
    app.run(debug=True,use_reloader=False, host="0.0.0.0",port='6969')