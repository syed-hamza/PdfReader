from flask import Flask, request, jsonify, render_template, redirect, url_for
from werkzeug.utils import secure_filename
from Libraries.transcriber import whisperTranscriber
# from Libraries.graphAgent import agent
from Libraries.graphAgentIndexing import agent
import json
import os
from langchain_openai import ChatOpenAI

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
transcriber = whisperTranscriber()
model = ChatOpenAI(model="gpt-4o")
tools = ["arxiv"]
chatAgent = agent(model, tools)
DATA_FILE = 'data/chats.json'

def load_conversations():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as file:
            return json.load(file)
    return []

def save_conversations(conversations):
    with open(DATA_FILE, 'w') as file:
        json.dump(conversations, file)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/conversations', methods=['GET'])
def get_conversations():
    conversations = load_conversations()
    return jsonify(conversations)

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    conversation_id = request.json.get('conversation_id')

    conversations = load_conversations()
    for conversation in conversations:
        if conversation['id'] == conversation_id:
            response_actions = chatAgent(user_message)
            response_message = chatAgent.getText()
            print(response_actions)
            conversation['messages'].append({'sender': 'user', 'text': user_message})
            conversation['messages'].append({'sender': 'bot', 'text': response_message})
            save_conversations(conversations)
            return jsonify(response_actions)

    return jsonify({'error': 'Conversation not found'}), 404

@app.route('/new_chat', methods=['POST'])
def new_chat():
    conversations = load_conversations()
    new_conversation = {'id': len(conversations) + 1, 'messages': []}
    conversations.append(new_conversation)
    save_conversations(conversations)
    return jsonify(new_conversation)

@app.route('/delete_chat/<int:conversation_id>', methods=['DELETE'])
def delete_chat(conversation_id):
    conversations = load_conversations()
    conversations = [conv for conv in conversations if conv['id'] != conversation_id]
    save_conversations(conversations)
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
        conversations = load_conversations()
        for conversation in conversations:
            if conversation['id'] == conversation_id:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                user_message = transcriber(filepath)
                response_actions = chatAgent(user_message)
                response_message = chatAgent.getText()
                conversation['messages'].append({'sender': 'user', 'text': user_message})
                conversation['messages'].append({'sender': 'bot', 'text': response_message})
                save_conversations(conversations)
                return jsonify(response_actions)
        return jsonify({'error': 'Conversation not found'}), 404
    return jsonify({'error': 'File upload failed'}), 400

if __name__ == '__main__':
    app.run(debug=True)
