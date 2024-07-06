const parseActions= (actions) =>{
    console.log(actions)
    actions.forEach(item => {
        const key = Object.keys(item)[0];
        const value = item[key];
        if(key==="newChat"){
            newChat()
        }
        if(key==="addMessage"){
            addmessage(value['input'],value['response'])
        }
        if(key==="display"){
            displayPDF(value)
        }
    })
}


const displayPDF = (url) => {
    const pdfEmbed = document.getElementById('pdfPlaceholder');
    const pdfFallback = document.getElementById('pdfFallback');

    if (url && url.trim() !== '') {
        pdfEmbed.setAttribute('src', url);
        pdfEmbed.classList.remove('hidden');
        pdfFallback.classList.add('hidden');
    } else {
        pdfEmbed.setAttribute('src', '');
        pdfEmbed.classList.add('hidden');
        pdfFallback.classList.remove('hidden');
    }
}

const addmessage = (userMessage,reply) => {
    const userMsgDiv = document.createElement('div');
    userMsgDiv.textContent = userMessage;
    userMsgDiv.className = 'p-2 bg-green-100 rounded self-end';
    messages.appendChild(userMsgDiv)

    const responseMsgDiv = document.createElement('div');
    responseMsgDiv.textContent = reply;
    responseMsgDiv.className = 'p-2 bg-gray-100 rounded self-start';
    messages.appendChild(responseMsgDiv);

}

