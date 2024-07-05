let currentConversationId = null;
let mediaRecorder;
let audioChunks = [];

const chatHistory = document.getElementById('chat-history');
const messages = document.getElementById('messages');
const messageInput = document.getElementById('message-input');
const audioIcon = document.getElementById('audio-icon');

const loadConversations = () => {
    fetch('/conversations')
        .then(response => response.json())
        .then(data => {
            chatHistory.innerHTML = '';
            if (data.length === 0) {
                newChat();
                return;
            }
            data.forEach(conversation => {
                const convDiv = document.createElement('div');
                convDiv.textContent = `Conversation ${conversation.id}`;
                convDiv.className = 'p-2 bg-white mb-2 rounded cursor-pointer';
                convDiv.onclick = () => loadConversation(conversation.id);
                chatHistory.appendChild(convDiv);
            });
            if (currentConversationId === null && data.length > 0) {
                loadConversation(data[0].id);
            }
        });
};

const loadConversation = (conversationId) => {
    fetch('/conversations')
        .then(response => response.json())
        .then(data => {
            const conversation = data.find(conv => conv.id === conversationId);
            if (conversation) {
                currentConversationId = conversation.id;
                messages.innerHTML = '';
                conversation.messages.forEach(msg => {
                    const msgDiv = document.createElement('div');
                    msgDiv.textContent = msg.text;
                    msgDiv.className = msg.sender === 'user' ? 'p-2 bg-green-100 rounded self-end' : 'p-2 bg-gray-100 rounded self-start';
                    messages.appendChild(msgDiv);
                });
            }
        });
};

const sendMessage = () => {
    const message = messageInput.value;
    if (message.trim() && currentConversationId !== null) {
        fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, conversation_id: currentConversationId })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error(data.error);
            } else {
                parseActions(data);
                messageInput.value = ''
            }
        });
    }
};

const newChat = () => {
    fetch('/new_chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(response => response.json())
    .then(newConversation => {
        currentConversationId = newConversation.id;
        messages.innerHTML = '';
        loadConversations();
    });
};

const deleteChat = () => {
    if (currentConversationId !== null) {
        fetch(`/delete_chat/${currentConversationId}`, {
            method: 'DELETE'
        })
        .then(response => {
            if (response.ok) {
                currentConversationId = null;
                loadConversations();
            }
        });
    }
};

const startRecording = () => {
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
            mediaRecorder = new MediaRecorder(stream);
            mediaRecorder.start();
            audioChunks = [];

            mediaRecorder.addEventListener('dataavailable', event => {
                audioChunks.push(event.data);
            });

            mediaRecorder.addEventListener('stop', () => {
                const audioBlob = new Blob(audioChunks);
                const audioFile = new File([audioBlob], 'audio.webm', { type: 'audio/webm' });

                const formData = new FormData();
                formData.append('audio', audioFile);

                fetch(`/upload_audio?convId=${currentConversationId}`, {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        console.error(data.error);
                    } else {
                        parseActions(data);
                    }
                });
            });
        });
};

const stopRecording = () => {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
    }
};

const toggleRecording = () => {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        stopRecording();
        audioIcon.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 14v4m0 0h-3m3 0h3m-3-4a4 4 0 00-4-4V9a4 4 0 108 0v1a4 4 0 00-4 4z" /></svg>';
    } else {
        startRecording();
        audioIcon.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>';
    }
};

document.addEventListener('DOMContentLoaded', loadConversations);
