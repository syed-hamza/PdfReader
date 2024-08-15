import cv2
import os
from moviepy.editor import VideoFileClip, AudioFileClip

class videoGenMethod():
    def __init__(self):
        pass

    def generateVideo(self, audio_path, image_dir, video_path, durations):
        # Get list of image files and sort them numerically
        images = [img for img in os.listdir(image_dir) if img.endswith(".jpg") or img.endswith(".png")]
        images.sort(key=lambda x: int(x.split('.')[0]))
        
        print(f"Number of images: {len(images)}, Number of durations: {len(durations)}")
        
        if not images:
            raise ValueError("No images found in the directory.")
        
        # Initialize video writer
        frame = cv2.imread(os.path.join(image_dir, images[0]))
        height, width, _ = frame.shape
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec for .mp4 file
        video = cv2.VideoWriter(video_path, fourcc, 15, (width, height))

        # Write each image to video with its corresponding duration
        for img, duration in zip(images, durations):
            frame = cv2.imread(os.path.join(image_dir, img))
            
            # Write the frame for the specified duration
            for _ in range(int(duration * 15)):
                video.write(frame)
        
        cv2.destroyAllWindows()
        video.release()
        
        self.add_audio_to_video(video_path, audio_path, video_path)
        print(f"Video saved as {video_path}")

    def add_audio_to_video(self, video_path, audio_path, output_path):
        # Load video and audio
        video_clip = VideoFileClip(video_path)
        audio_clip = AudioFileClip(audio_path)
        
        # Set audio to the video
        video_clip = video_clip.set_audio(audio_clip)
        
        # Write the result to a file
        video_clip.write_videofile(output_path, codec='libx264')
        print(f"Video with audio saved as {output_path}")