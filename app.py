import streamlit as st
from pymongo import MongoClient
from audio_separator.separator import Separator
from moviepy.editor import VideoFileClip, AudioFileClip
from io import BytesIO
import zipfile
import os
import tempfile
import time

# MongoDB connection URI
mongo_uri = "mongodb+srv://businesssaboorhassan:<password>@nusicdel.e8riwde.mongodb.net/?retryWrites=true&w=majority&appName=nusicdel"

# Initialize MongoDB client
client = MongoClient(mongo_uri)
db = client["audio_video"]
collection = db["video_audio_files"]

# Initialize audio separator
separator = Separator()

def process_video(video_file):
    st.write("Processing video...")

    # Generate output filename
    output_filename = f"{video_file.name.split('.')[0]}_vocals.mp4"

    # Save video file temporarily
    with tempfile.NamedTemporaryFile(delete=False) as temp_video:
        temp_video.write(video_file.read())

    # Perform audio separation
    clip = VideoFileClip(temp_video.name)
    audio = clip.audio
    audio_path = tempfile.mktemp(suffix=".wav")
    audio.write_audiofile(audio_path)

    try:
        output_file_paths = separator.separate(audio_path)

        # Combine vocals with original video
        combined_clip = clip.set_audio(AudioFileClip(output_file_paths[0]))
        combined_clip.write_videofile(output_filename, codec="libx264", audio_codec="aac")

        st.success(f"Processed video: {output_filename}")

    except Exception as e:
        st.error(f"Error processing video: {str(e)}")

    finally:
        # Delete temporary files
        os.remove(temp_video.name)
        os.remove(audio_path)
        if len(output_file_paths) > 0:
            os.remove(output_file_paths[0])

    return output_filename

def upload_and_process_files(file):
    if isinstance(file, list):
        for f in file:
            process_video(f)
    else:
        return process_video(file)

def main():
    st.title("Video Audio Separation App")

    file = st.file_uploader("Upload a video file or a zip file containing videos", type=["mp4", "zip"])

    if file is not None:
        if isinstance(file, list) or zipfile.is_zipfile(file):
            if isinstance(file, list):
                uploaded_files = file
            else:
                with zipfile.ZipFile(file) as zip_ref:
                    zip_ref.extractall("./temp")
                    uploaded_files = [os.path.join("./temp", name) for name in zip_ref.namelist()]

            st.write("Processing multiple videos...")

            # Process each uploaded file
            for f in uploaded_files:
                upload_and_process_files(f)

            # Create a zip file with processed videos
            zip_filename = f"processed_videos_{int(time.time())}.zip"
            with zipfile.ZipFile(zip_filename, "w") as zip_file:
                for f in uploaded_files:
                    processed_filename = f"{os.path.splitext(os.path.basename(f))[0]}_vocals.mp4"
                    zip_file.write(processed_filename)

            st.markdown(f"Download processed videos: [Processed Videos]({zip_filename})")
            
            # Clean up processed files after 1 hour
            time.sleep(3600)
            for f in uploaded_files:
                os.remove(f)

        else:
            # Single video file upload
            uploaded_file = file
            output_filename = upload_and_process_files(uploaded_file)
            st.markdown(f"Download processed video: [Processed Video]({output_filename})")

            # Clean up processed file after 1 hour
            time.sleep(3600)
            os.remove(output_filename)

if __name__ == "__main__":
    main()
