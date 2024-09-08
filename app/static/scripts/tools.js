const parseActions = (data) => {
    console.log(data);
    const actions = data.actions;

    actions.forEach(item => {
        const key = Object.keys(item)[0];
        const value = item[key];
        console.log("key:",key)
        console.log("value:",value)
        if(key === "newChat"){
            newChat();
        }
        if(key === "addMessage"){
            let response = value['response']
            addmessage(value['input'],response)
        }
        if(key === "display"){
            displayPDF(value);
        }
    });
};

// const displayRetrievedImages = (images) => {
//     const imageContainer = document.getElementById('imageContainer');
//     imageContainer.innerHTML = ''; // Clear previous images

//     images.forEach(imagePath => {
//         const img = document.createElement('img');
//         img.src = imagePath;
//         img.className = 'w-full mb-2 rounded';
//         imageContainer.appendChild(img);
//     });
// }

const getPDFName = ()=>{
    const pdfSelect = document.getElementById('element-select');
    const pdfName = pdfSelect.value
    return pdfName
}

const addmessage = (userMessage, reply, audioPath = null) => {
    if(userMessage !== ''){
        const userMsgDiv = document.createElement('div');
        userMsgDiv.textContent = userMessage;
        userMsgDiv.className = 'p-2 bg-green-100 rounded self-end';
        messages.appendChild(userMsgDiv);
    }
    if(reply !== ''){
        const responseMsgDiv = document.createElement('div');
        responseMsgDiv.className = 'p-2 bg-gray-100 rounded self-start';
        messages.appendChild(responseMsgDiv);

        // Process the reply to replace image paths with base64 encoded images
        const processedReply = reply.replace(/<img src='(.*?)'><\/img>/g, (match, p1) => {
            try {
                const imageFile = new File([p1], 'image.jpeg', { type: 'image/jpeg' });
                const reader = new FileReader();
                reader.readAsDataURL(imageFile);
                reader.onloadend = () => {
                    const base64data = reader.result;
                    return `<img src="${base64data}" alt="Embedded Image">`;
                };
            } catch (error) {
                return `[Image not found: ${p1}]`;
            }
        });

        // Check if markdown-it is available
        if (typeof markdownit === 'function') {
            const md = markdownit({
                html: true,
                linkify: true,
                typographer: true,
                highlight: function (str, lang) {
                    if (lang && hljs.getLanguage(lang)) {
                        try {
                            return hljs.highlight(str, { language: lang }).value;
                        } catch (__) {}
                    }
                    return ''; // use external default escaping
                }
            });
            responseMsgDiv.innerHTML = md.render(processedReply);
        } else {
            // Fallback if markdown-it is not available
            responseMsgDiv.textContent = processedReply;
            console.warn('markdown-it is not available. Displaying plain text.');
        }
        if (typeof hljs !== 'undefined') {
            responseMsgDiv.querySelectorAll('pre code').forEach((block) => {
                hljs.highlightBlock(block);
            });
        } else {
            console.warn('highlight.js is not available. Code blocks will not be highlighted.');
        }
    }
};

function loadPDF(pdfName) {
    console.log("loading: ", pdfName);
    fetch(`/get-pdf?filename=${pdfName}`)
        .then(response => response.blob())
        .then(blob => {
            const url = URL.createObjectURL(blob);
            const viewer = document.getElementById('pdfPlaceholder');
            viewer.src = url;
        })
        .catch(error => console.error('Error:', error));
}

function displayAlert(message, type = "normal") {
    var alertBox = document.getElementById('alert-box');
    var alertMessage = document.getElementById('alert-message');
  
    // Set the message
    alertMessage.innerText = message;
  
    // Set the background color based on the type
    if (type === 'normal') {
        alertBox.classList.remove('bg-yellow-500');
        alertBox.classList.remove('bg-red-500');
        alertBox.classList.add('bg-green-500');
    } else if (type === 'danger') {
        alertBox.classList.remove('bg-green-500');
        alertBox.classList.remove('bg-red-500');
        alertBox.classList.add('bg-yellow-500');
    }else if (type === 'error') {
        alertBox.classList.remove('bg-yellow-500');
        alertBox.classList.remove('bg-green-500');
        alertBox.classList.add('bg-red-500');
    }
  
    // Show the alert box
    alertBox.style.transform = 'translateY(0)';
    alertBox.style.opacity = '1';
  
    // Hide the alert box after 1400ms
    setTimeout(function() {
        alertBox.style.transform = 'translateY(-100%)';
        alertBox.style.opacity = '0';
    }, 1400);
  }


function showprogress(message, type = "normal") {
    var alertBox = document.getElementById('alert-box');
    var alertMessage = document.getElementById('alert-message');
  
    // Set the message
    alertMessage.innerHTML = message;
  
    // Set the background color based on the type
    if (type === 'normal') {
        alertBox.classList.remove('bg-yellow-500');
        alertBox.classList.remove('bg-red-500');
        alertBox.classList.add('bg-green-500');
    } else if (type === 'danger') {
        alertBox.classList.remove('bg-green-500');
        alertBox.classList.remove('bg-red-500');
        alertBox.classList.add('bg-yellow-500');
    }else if (type === 'error') {
        alertBox.classList.remove('bg-yellow-500');
        alertBox.classList.remove('bg-green-500');
        alertBox.classList.add('bg-red-500');
    }
  
    // Show the alert box
    alertBox.style.transform = 'translateY(0)';
    alertBox.style.opacity = '1';
  }




  function hideprogress(Message = null) {
    if(Message != null){
        displayAlert(Message, type = "normal")
    }
    else{
        var alertBox = document.getElementById('alert-box');
        setTimeout(function() {
            alertBox.style.transform = 'translateY(-100%)';
            alertBox.style.opacity = '0';
        }, 10);
    }
  }
