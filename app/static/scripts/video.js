
function NonePdf(){
    if(localStorage.getItem("pdf")==None){
        console.log("pdf is none")
        
    }
}
function loadImage(path) {
    // Set the image source dynamically
    document.getElementById('imagePlaceholder').src = path;
}
document.addEventListener("DOMContentLoaded", function() {
    fetch(`/get_video_path?pdfName=${localStorage.getItem("pdf")}`)
        .then(response => response.json())
        .then(data => {
            let videoPlayer = document.getElementById("videoPlayer");
            videoPlayer.src = data.video_url;
            videoPlayer.load();
            videoPlayer.play();
        });
});

document.getElementById("videoPlayer").addEventListener("timeupdate", function() {
    let videoPlayer = document.getElementById("videoPlayer");
    let currentTime = videoPlayer.currentTime;

    if (videoPlayer.paused || videoPlayer.ended) return;

    // Send the current timestamp to the server every 0.5 seconds
    console.log("sinding pdf",localStorage.getItem("pdf"))
    fetch('/update_timestamp', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ timestamp: currentTime ,pdfName :localStorage.getItem("pdf")})
    });
});
setInterval(function() {
    let videoPlayer = document.getElementById("videoPlayer");
    if (!videoPlayer.paused && !videoPlayer.ended) {
        let currentTime = videoPlayer.currentTime;
        fetch('/update_timestamp', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ timestamp: currentTime,pdfName :localStorage.getItem("pdf") })
        })
        .then(response => response.text())
        .then(path =>loadImage(path))
    }
}, 500);