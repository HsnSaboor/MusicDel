import streamlit as st
import os
import subprocess
import zipfile
import requests
import speech_recognition as sr
from spleeter.separator import Separator
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from moviepy.editor import VideoFileClip
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

# Initialize Spleeter separator
separator = Separator('spleeter:2stems')

# Authenticate and initialize PyDrive
def authenticate_drive(client_id, client_secret):
    gauth = GoogleAuth()
    gauth.settings['client_config_backend'] = 'settings'
    gauth.settings['client_config'] = {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": "http://localhost:8080/"
    }
    gauth.LocalWebserverAuth()  # Creates local webserver and auto handles authentication
    return GoogleDrive(gauth)

# Helper function to download file from URL
def download_file(url, dest_path):
    response = requests.get(url, stream=True)
    with open(dest_path, 'wb') as file:
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)

# Retry upload in case of network errors
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=retry_if_exception_type(Exception))
def upload_to_drive(file_path, drive):
    file_name = os.path.basename(file_path)
    gfile = drive.CreateFile({'title': file_name})
    gfile.SetContentFile(file_path)
    gfile.Upload()

# Helper function to transcribe audio using Google Speech Recognition
def transcribe_audio(audio_path):
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_path) as source:
        audio = recognizer.record(source)
        try:
            return recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            return "Transcription failed: Audio not clear."
        except sr.RequestError:
            return "Transcription failed: Could not request results."

# Helper function to remove audio from video
def remove_audio_from_video(video_path, output_format='webm'):
    video = VideoFileClip(video_path)
    video_no_audio = video.without_audio()
    output_path = os.path.splitext(video_path)[0] + f"_no_audio.{output_format}"
    video_no_audio.write_videofile(output_path, codec='libvpx' if output_format == 'webm' else 'libx264')
    return output_path

# Streamlit app
st.title("Video to Vocal Separation App")

# Input Google API credentials
client_id = st.text_input("Enter your Google API Client ID")
client_secret = st.text_input("Enter your Google API Client Secret", type="password")

# Authenticate Google Drive
if client_id and client_secret:
    drive = authenticate_drive(client_id, client_secret)
    st.success("Authenticated with Google Drive successfully.")

    # Upload options
    st.subheader("Choose upload option:")
    upload_option = st.selectbox("", ["Upload multiple videos", "Upload single video", "Upload zip file", "Provide link to zip file"])

    if upload_option == "Upload multiple videos":
        uploaded_files = st.file_uploader("Upload multiple videos", accept_multiple_files=True, type=["mp4", "mkv"])
        
        if uploaded_files:
            for uploaded_file in uploaded_files:
                with st.spinner(f"Processing {uploaded_file.name}..."):
                    video_path = os.path.join(".", uploaded_file.name)
                    with open(video_path, 'wb') as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Process the uploaded video
                    process_video(video_path, drive)
    
    elif upload_option == "Upload single video":
        uploaded_file = st.file_uploader("Upload a single video", type=["mp4", "mkv"])
        
        if uploaded_file:
            with st.spinner(f"Processing {uploaded_file.name}..."):
                video_path = os.path.join(".", uploaded_file.name)
                with open(video_path, 'wb') as f:
                    f.write(uploaded_file.getbuffer())
                
                # Process the uploaded video
                process_video(video_path, drive)
    
    elif upload_option == "Upload zip file":
        uploaded_zip = st.file_uploader("Upload a zip file containing videos", type=["zip"])
        
        if uploaded_zip:
            with st.spinner("Processing uploaded zip file..."):
                zip_path = "./uploaded_videos.zip"
                with open(zip_path, "wb") as f:
                    f.write(uploaded_zip.getbuffer())
                
                # Extract the zip file
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall("./input_videos")
                
                # Process each video file in the extracted folder
                for root, dirs, files in os.walk("./input_videos"):
                    for file in files:
                        if file.endswith('.mp4') or file.endswith('.mkv'):
                            video_path = os.path.join(root, file)
                            process_video(video_path, drive)
    
    elif upload_option == "Provide link to zip file":
        zip_url = st.text_input("Enter URL of the zip file containing videos")
        if st.button("Process"):
            if zip_url:
                with st.spinner("Downloading zip file..."):
                    zip_path = "./downloaded_videos.zip"
                    download_file(zip_url, zip_path)
                
                # Extract the zip file
                with st.spinner("Extracting zip file..."):
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall("./input_videos")
                    
                    # Process each video file in the extracted folder
                    for root, dirs, files in os.walk("./input_videos"):
                        for file in files:
                            if file.endswith('.mp4') or file.endswith('.mkv'):
                                video_path = os.path.join(root, file)
                                process_video(video_path, drive)

# Function to process each video
def process_video(video_path, drive):
    st.write(f"Processing {os.path.basename(video_path)}...")
    
    # Extract audio
    audio_path = os.path.splitext(video_path)[0] + '.aac'
    subprocess.run(['ffmpeg', '-i', video_path, '-c:a', 'aac', '-b:a', '128k', audio_path])
    
    # Convert audio to WAV
    wav_path = os.path.splitext(video_path)[0] + '.wav'
    subprocess.run(['ffmpeg', '-i', audio_path, '-ar', '16000', wav_path])
    
    # Separate music from audio
    output_path = os.path.splitext(video_path)[0]
    separator.separate_to_file(wav_path, output_path)
    
    # Transcribe vocals
    vocal_path = os.path.join(output_path, 'vocals.wav')
    transcription = transcribe_audio(vocal_path)
    transcription_path = os.path.join(output_path, 'transcription.txt')
    with open(transcription_path, 'w') as f:
        f.write(transcription)
    
    # Remove audio from video
    video_no_audio_path = remove_audio_from_video(video_path)
    
    # Upload results to Google Drive
    try:
        for root_output, dirs_output, files_output in os.walk(output_path):
            for file_output in files_output:
                local_output_path = os.path.join(root_output, file_output)
                upload_to_drive(local_output_path, drive)
                st.write(f"Uploaded {file_output} to Google Drive.")
        
        # Upload video without audio
        upload_to_drive(video_no_audio_path, drive)
        st.write(f"Uploaded {os.path.basename(video_no_audio_path)} to Google Drive.")
    except Exception as e:
        st.error(f"Failed to upload {file_output} due to {str(e)}")

    st.success(f"{os.path.basename(video_path)} processing complete!")

