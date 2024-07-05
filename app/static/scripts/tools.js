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


const displayPDF = (url)=>{
    pdfEmbed = document.getElementById('pdfPlaceholder')
    pdfEmbed.setAttribute('src', url);
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

