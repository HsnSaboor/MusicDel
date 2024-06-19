import streamlit as st
from audio_separator.separator import Separator
from moviepy.editor import VideoFileClip, AudioFileClip
from io import BytesIO
import zipfile
import os
import tempfile
import subprocess
import time
import shutil

# Initialize audio separator
separator = Separator()

def get_ffmpeg_path():
    # Try to get the ffmpeg path using shutil.which
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        # If shutil.which returns None, try to find it in the PATH environment variable
        try:
            result = subprocess.run(['which', 'ffmpeg'], capture_output=True, text=True)
            ffmpeg_path = result.stdout.strip()
        except subprocess.CalledProcessError:
            ffmpeg_path = None

    return ffmpeg_path

def process_video(video_file, ffmpeg_path):
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
        if ffmpeg_path is None:
            raise FileNotFoundError("FFmpeg not found. Please make sure it is installed and in the system PATH.")

        st.write(f"Using FFmpeg at: {ffmpeg_path}")

        output_file_paths = separator.separate(audio_path)

        # Combine vocals with original video
        combined_clip = clip.set_audio(AudioFileClip(output_file_paths[0]))
        combined_clip.write_videofile(output_filename, codec="libx264", audio_codec="aac")

        st.success(f"Processed video: {output_filename}")

        # Optionally save processed files to a specific folder
        processed_folder = "processed_videos"
        if not os.path.exists(processed_folder):
            os.makedirs(processed_folder)

        processed_filepath = os.path.join(processed_folder, output_filename)
        combined_clip.write_videofile(processed_filepath, codec="libx264", audio_codec="aac")

        st.markdown(f"Download processed video: [Processed Video]({processed_filepath})")

    except Exception as e:
        st.error(f"Error processing video: {str(e)}")

    finally:
        # Delete temporary files
        os.remove(temp_video.name)
        os.remove(audio_path)
        if len(output_file_paths) > 0:
            os.remove(output_file_paths[0])

    return output_filename

def upload_and_process_files(files, ffmpeg_path):
    if isinstance(files, list):
        for file in files:
            process_video(file, ffmpeg_path)
    else:
        return process_video(files, ffmpeg_path)

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

            ffmpeg_path = get_ffmpeg_path()

            # Process each uploaded file
            for uploaded_file in uploaded_files:
                upload_and_process_files(uploaded_file, ffmpeg_path)

            # Clean up temporary files after processing
            for f in uploaded_files:
                if isinstance(f, str) and os.path.exists(f):
                    os.remove(f)

        else:
            # Single video file upload
            uploaded_file = file
            ffmpeg_path = get_ffmpeg_path()
            output_filename = upload_and_process_files(uploaded_file, ffmpeg_path)

            # Clean up processed file after displaying link
            if os.path.exists(output_filename):
                os.remove(output_filename)

if __name__ == "__main__":
    main()
