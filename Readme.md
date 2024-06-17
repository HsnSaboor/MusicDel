# Video to Vocal Separation App 🎵🎥

This Streamlit app allows users to upload videos, separate vocals from the audio, transcribe vocals into text, and download videos without audio. It utilizes Google Cloud APIs for transcription and Google Drive for storage.

## Features

- **Upload Options:** Upload multiple videos, a single video, or a zip file containing videos.
- **Processing:** Separates vocals from uploaded videos, transcribes vocal audio to text.
- **Output:** Provides download links for separated vocal audio, transcription text file, and video without audio.

## How to Use

1. **Upload Videos:**
   - Choose an upload option (multiple videos, single video, zip file, or link to a zip file).
   
2. **Processing:**
   - The app will process each video, separating vocals and transcribing the vocal audio into text.

3. **Download Outputs:**
   - Once processing is complete, download links will be provided for each output (vocal audio, transcription text, video without audio).

## Deployment

The app is deployed on Streamlit Cloud and connected to a GitHub repository for continuous deployment. To deploy your own version:

1. Clone this repository:
   ```bash
   git clone https://github.com/your-username/streamlit-app.git
   cd streamlit-app
