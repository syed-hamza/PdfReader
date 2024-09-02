async function uploadImage(file) {
    const formData = new FormData();
    formData.append('image', file);

    const response = await fetch('/upload-image', {
        method: 'POST',
        body: formData
    });

    const data = await response.json();
    if (data.success) {
        const imgElement = document.createElement('img');
        imgElement.src = `data:image/png;base64,${data.base64}`;
        console.log(data.data)
        document.getElementById('messages').appendChild(imgElement);
    } else {
        alert('Image upload failed.');
    }
}

function setupDropArea(dropid = 'messages'){
    const dropArea = document.getElementById(dropid);

    dropArea.addEventListener('dragover', (event) => {
        event.preventDefault();
        dropArea.classList.add('bg-gray-300');
    });

    dropArea.addEventListener('dragleave', (event) => {
        event.preventDefault();
        dropArea.classList.remove('bg-gray-300');
    });

    dropArea.addEventListener('drop', (event) => {
        event.preventDefault();
        dropArea.classList.remove('bg-gray-300');
        
        const files = event.dataTransfer.files;
        if (files.length > 0) {
            const file = files[0];
            if (file.type.startsWith('image/')) {
                uploadImage(file);
            } else {
                alert('Please drop an image file.');
            }
        }
})}