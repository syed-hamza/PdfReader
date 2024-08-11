const parseActions = (data) => {
    console.log(data);
    const actions = data.actions;
    const retrievedImages = data.retrieved_images;

    actions.forEach(item => {
        const key = Object.keys(item)[0];
        const value = item[key];
        if(key === "newChat"){
            newChat();
        }
        if(key === "addMessage"){
            addmessage(value['input'], data.message);
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

const addmessage = (userMessage, reply) => {
    const userMsgDiv = document.createElement('div');
    userMsgDiv.textContent = userMessage;
    userMsgDiv.className = 'p-2 bg-green-100 rounded self-end';
    messages.appendChild(userMsgDiv);

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

    // Apply syntax highlighting to code blocks
    if (typeof hljs !== 'undefined') {
        responseMsgDiv.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightBlock(block);
        });
    } else {
        console.warn('highlight.js is not available. Code blocks will not be highlighted.');
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