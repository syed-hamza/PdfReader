from flask import Flask, request, jsonify, render_template, redirect, url_for
from werkzeug.utils import secure_filename
from Libraries.chathandler import chathandler
import os
from flask import send_file

app = Flask(__name__)
chatHandler = chathandler()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test')
def test():
    return render_template('test.html')

@app.route('/conversations', methods=['GET'])
def get_conversations():
    conversations = chatHandler.load_conversations()
    return jsonify(conversations)


@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    conversation_id = request.json.get('conversation_id')
    return chatHandler.chat(conversation_id,user_message)


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

if __name__ == '__main__':
    app.run(debug=True,use_reloader=False)
