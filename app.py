import streamlit as st
import os
from pathlib import Path
from openai import OpenAI

# Function to transcribe the audio using OpenAI's Whisper model
def transcribe_audio(audio_file_path):
    """
    This function will use the OpenAI client to transcribe the audio file
    and return the transcribed text.
    """
    try:
        client = OpenAI(api_key=st.secrets["API"])
        with open(audio_file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
              model="whisper-1", 
              file=audio_file)
        return transcript.text
    except Exception as e:
        # If there's an error, print it out on the app
        st.error(f"An error occurred during transcription: {e}")
        return None

# Function to save the uploaded file to a temporary directory
def save_uploaded_file(uploaded_file):
    try:
        Path("tempDir").mkdir(parents=True, exist_ok=True)
        file_path = os.path.join("tempDir", uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    except Exception as e:
        st.error(f"Failed to save file: {e}")
        return None

def main():
    st.title('Audio Transcription App')

    # User file upload section
    uploaded_file = st.file_uploader("Choose an audio file...", type=["mp3", "wav", "ogg", "m4a"])

    if uploaded_file is not None:
        # Save the file to a temporary directory
        saved_file_path = save_uploaded_file(uploaded_file)
        if saved_file_path:
            # File saved successfully
            st.audio(saved_file_path)
            st.write("Transcribing... This may take a while for large files.")
            
            # Transcribe the audio
            transcription = transcribe_audio(saved_file_path)
            
            # Display the transcription if successful
            if transcription:
                st.text_area("Transcription:", transcription, height=300)
            # Cleanup the temporary file
            os.remove(saved_file_path)
        else:
            st.error("Failed to save the file.")
    else:
        st.info("Please upload an audio file.")

# Run the app
if __name__ == "__main__":
    main()
