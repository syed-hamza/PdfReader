let currentConversationId = null;
let mediaRecorder;
let audioChunks = [];
var initid = 'paragraph-1';
const chatHistory = document.getElementById('chat-history');
const audioIcon = document.getElementById('audio-icon');

const loadConversations = () => {
    const chatHistory = document.getElementById('chat-history');
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
    const messages = document.getElementById('messages');
    fetch('/conversations')
        .then(response => response.json())
        .then(data => {
            const conversation = data.find(conv => conv.id === conversationId);
            if (conversation) {
                currentConversationId = conversation.id;
                messages.innerHTML = '';
                conversation.messages.forEach(msg => {
                    // const msgDiv = document.createElement('div');
                    // msgDiv.textContent = msg.text;
                    // msgDiv.className = msg.sender === 'user' ? 'p-2 bg-green-100 rounded self-end' : 'p-2 bg-gray-100 rounded self-start';
                    // messages.appendChild(msgDiv);
                    if(msg.sender === 'user')
                        addmessage(msg.text,'')
                    else
                        addmessage('',msg.text)
                });
            }
        });
};

const sendMessage = () => {
    const messageInput = document.getElementById('message-input');
    const message = messageInput.value;
    if (message.trim() && currentConversationId !== null) {
        fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, conversation_id: currentConversationId })
        })
        .then(response => response.json())
        .then(async(data)=> {
            if (data.error) {
                console.error(data.error);
            } else {
                if(data.numImages>0){
                    var imageText = await getimage()
                    parseActions(data,imageText);
                }
                else{
                    parseActions(data);
                }
                messageInput.value = ''
            }
        });
    }
};

const getimage = async () => {
    const response = await fetch('/getImage', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    });
    const data = await response.text();
    return data;
}


const newChat = () => {
    const messages = document.getElementById('messages');
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
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
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
            })
            .catch(error => console.error('Error accessing media devices.', error));
    } else {
        console.error('getUserMedia is not supported in this browser.');
    }
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

// Function to fetch elements from the server
function fetchElements() {
    fetch('/get-elements')
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById('element-select');
            select.innerHTML = '';
            data.forEach(element => {
                const option = document.createElement('option');
                option.value = element;
                option.textContent = element;
                select.appendChild(option);
            });
            if(data.length>0){
                localStorage.setItem("pdf",data[0])
                loadPDF(data[0])
            }
        })
        .catch(error => console.error('Error fetching elements:', error));
}


// PDF upload functionality
function setupPDFUpload() {
    const dropZone = document.getElementById('pdf-upload');
    const fileInput = document.getElementById('pdf-input');

    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.style.backgroundColor = '#f0f0f0';
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.style.backgroundColor = '';
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.style.backgroundColor = '';
        const file = e.dataTransfer.files[0];
        if (file && file.type === 'application/pdf') {
            uploadPDF(file);
        } else {
            alert('Please upload a PDF file.');
        }
    });

    fileInput.addEventListener('change', () => {
        const file = fileInput.files[0];
        if (file && file.type === 'application/pdf') {
            uploadPDF(file);
        } else {
            alert('Please upload a PDF file.');
        }
    });
}

async function uploadPDF(file) {
    const formData = new FormData();
    formData.append('pdf', file);
    showprogress("Uploading Research Papers", type = "normal")
    await fetch('/upload-pdf', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            hideprogress("Upload Succesful")
            fetchElements();
            loadPDF(data["fileName"])
        } else {
            hideprogress('Failed to upload PDF.', type="error")
        }

    })
    .catch(error => console.error('Error uploading PDF:', error));
}

async function summarize(){
    const pdfSelect = document.getElementById('element-select');
    const pdfname = pdfSelect.value
    if(pdfname== null){
        console.log("no element selected")
        return;
    }
    document.getElementById('loader').style.display = 'inline-block';
    await fetch(`/getSummary?filename=${pdfname}`)
        .then(response => response.text())
        .then(
            response => addmessage('',response)
        )
        .catch(error => console.error('Error:', error));
    document.getElementById('loader').style.display = 'none';
    LoadAudio()
    
}
function displayVid(){
    window.location.href = "/video";
}

function LoadAudio() {
    const audioSource = document.getElementById('audioSource');
    const audioPlayer = document.getElementById('audioPlayer');
    const audioContainer = document.getElementById('audioContainer');
    audioSource.src = `/get_audio?pdfName=${localStorage.getItem("pdf")}`;
    audioPlayer.load();
    audioContainer.style.display = 'block';
}

function audioTimer() {
    let audioPlayer = document.getElementById("audioPlayer");

    audioPlayer.addEventListener("timeupdate",async function() {
        let currentTime = audioPlayer.currentTime;

        if (audioPlayer.paused || audioPlayer.ended) return;

        // Send the current timestamp to the server every 0.5 seconds
        var id = await fetch('/update_timestamp', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ timestamp: currentTime, pdfName: localStorage.getItem("pdf") })
        })
        .then(response => response.text());
        id = `paragraph-${id}`
        console.log("id: ",id)
        if(id != initid){
            var initparagraph = document.getElementById(initid)
            initparagraph.style.backgroundColor = '';
            var paragraph = document.getElementById(id)
            paragraph.style.backgroundColor = 'yellow'; 
            initid = id
        }
    });
}
function init() {
    // loadConversations();
    fetchElements();
    setupPDFUpload();
    audioTimer();
    setupDropArea();
    const pdfSelect = document.getElementById('element-select');
    localStorage.setItem("pdf",pdfSelect.value)
    console.log(localStorage.getItem("pdf"))
    pdfSelect.addEventListener('change', function() {
        if (this.value) {
            localStorage.setItem("pdf",this.value)
            loadPDF(this.value);
        }
    });
}

document.addEventListener('DOMContentLoaded', init);
