import streamlit as st
import os
from pathlib import Path
from openai import OpenAI
from pydub import AudioSegment

system_message = """
You will be presented with a stream of consciousness transcript. Your job is to regurgitate the entire transcript and leave out NONE of the key ideas, in the exact language of the original 
transcript whenever possible and present the content in the same order as the transcript. However, the text you return should be a cleaned up version of the transcript and be 'all meat, no fat.' This does not mean to leave out ANY self-contained ideas
(do not leave out any), but rather to present the SAME ideas in a slightly cleaner format so it doesn't read like a rambling stream of consciousness and instead is a cleaned up regurgitation of it.
"""

# Initialize session state
if 'transcription' not in st.session_state:
    st.session_state.transcription = ""
if 'processed_info' not in st.session_state:
    st.session_state.processed_info = ""

# Function to transcribe the audio using OpenAI's Whisper model
def transcribe_audio(audio_file_path):
    try:
        client = OpenAI(api_key=st.secrets["API"])
        with open(audio_file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        return transcript.text
    except Exception as e:
        st.error(f"An error occurred during transcription: {e}")
        return None

# Function to save the uploaded file to a temporary directory and convert to MP3
def save_and_convert_uploaded_file(uploaded_file):
    try:
        Path("tempDir").mkdir(parents=True, exist_ok=True)
        original_file_path = os.path.join("tempDir", uploaded_file.name)
        with open(original_file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Convert to MP3
        audio = AudioSegment.from_file(original_file_path)
        mp3_file_path = os.path.join("tempDir", f"{Path(uploaded_file.name).stem}.mp3")
        audio.export(mp3_file_path, format="mp3")

        # Remove the original file after conversion
        os.remove(original_file_path)

        return mp3_file_path
    except Exception as e:
        st.error(f"Failed to save or convert file: {e}")
        return None

# Function to split audio file into smaller chunks
def split_audio(input_file, max_duration_ms=20*60*1000):
    audio = AudioSegment.from_file(input_file)
    duration_ms = len(audio)

    parts = []
    for start_ms in range(0, duration_ms, max_duration_ms):
        end_ms = min(start_ms + max_duration_ms, duration_ms)
        part = audio[start_ms:end_ms]
        part_file_path = f"tempDir/{os.path.basename(input_file).split('.')[0]}_part{start_ms // max_duration_ms + 1}.mp3"
        part.export(part_file_path, format="mp3")
        parts.append(part_file_path)

    return parts

# Function to process the transcript with GPT-4o
def process_transcript(transcript):
    try:
        client = OpenAI(api_key=st.secrets["API"])
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": transcript}
            ]
        )
        return completion.choices[0].message.content

    except Exception as e:
        st.error(f"An error occurred during processing: {e}")
        return None

st.title('Transcribe Audio')

# User file upload section
uploaded_file = st.file_uploader("Choose an audio file...", type=["mp3", "wav", "ogg", "m4a"])

if uploaded_file is not None:
    # Save the file to a temporary directory and convert to MP3
    saved_file_path = save_and_convert_uploaded_file(uploaded_file)
    if saved_file_path:
        # File saved and converted successfully
        st.audio(saved_file_path)
        st.write("Transcribing... This may take a while for large files.")

        # Split the audio file if it is too long
        audio = AudioSegment.from_file(saved_file_path)
        if len(audio) > 20 * 60 * 1000:
            st.write("The audio file is too large and will be processed in chunks.")
            parts = split_audio(saved_file_path)
        else:
            parts = [saved_file_path]

        # Transcribe each part
        transcription = ""
        for part in parts:
            part_transcription = transcribe_audio(part)
            if part_transcription:
                transcription += part_transcription
            os.remove(part)

        # Store the transcription in session state
        st.session_state.transcription = transcription

        # Display the transcription if successful
        if transcription:
            st.text_area("Raw transcript:", transcription, height=300)
            with st.spinner('Processing transcript...'):
                processed_info = process_transcript(st.session_state.transcription)
            st.write("Processed Transcript:", st.session_state.processed_info, height=300)
        else:
            st.error("Transcription failed.")

        # Cleanup the temporary file
        os.remove(saved_file_path)
    else:
        st.error("Failed to save the file.")
else:
    st.info("Please upload an audio file.")

# import streamlit as st
# import os
# from pathlib import Path
# from openai import OpenAI
# from pydub import AudioSegment

# # Function to transcribe the audio using OpenAI's Whisper model
# def transcribe_audio(audio_file_path):
#     try:
#         client = OpenAI(api_key=st.secrets["API"])
#         with open(audio_file_path, "rb") as audio_file:
#             transcript = client.audio.transcriptions.create(
#               model="whisper-1", 
#               file=audio_file
#             )
#         return transcript.text
#     except Exception as e:
#         st.error(f"An error occurred during transcription: {e}")
#         return None

# # Function to save the uploaded file to a temporary directory and convert to MP3
# def save_and_convert_uploaded_file(uploaded_file):
#     try:
#         Path("tempDir").mkdir(parents=True, exist_ok=True)
#         original_file_path = os.path.join("tempDir", uploaded_file.name)
#         with open(original_file_path, "wb") as f:
#             f.write(uploaded_file.getbuffer())
        
#         # Convert to MP3
#         audio = AudioSegment.from_file(original_file_path)
#         mp3_file_path = os.path.join("tempDir", f"{Path(uploaded_file.name).stem}.mp3")
#         audio.export(mp3_file_path, format="mp3")
        
#         # Remove the original file after conversion
#         os.remove(original_file_path)
        
#         return mp3_file_path
#     except Exception as e:
#         st.error(f"Failed to save or convert file: {e}")
#         return None

# # Function to split audio file into smaller chunks
# def split_audio(input_file, max_duration_ms=20*60*1000):
#     audio = AudioSegment.from_file(input_file)
#     duration_ms = len(audio)

#     parts = []
#     for start_ms in range(0, duration_ms, max_duration_ms):
#         end_ms = min(start_ms + max_duration_ms, duration_ms)
#         part = audio[start_ms:end_ms]
#         part_file_path = f"tempDir/{os.path.basename(input_file).split('.')[0]}_part{start_ms // max_duration_ms + 1}.mp3"
#         part.export(part_file_path, format="mp3")
#         parts.append(part_file_path)

#     return parts

# st.title('Transcribe Audio')

# # User file upload section
# uploaded_file = st.file_uploader("Choose an audio file...", type=["mp3", "wav", "ogg", "m4a"])

# if uploaded_file is not None:
#     # Save the file to a temporary directory and convert to MP3
#     saved_file_path = save_and_convert_uploaded_file(uploaded_file)
#     if saved_file_path:
#         # File saved and converted successfully
#         st.audio(saved_file_path)
#         st.write("Transcribing... This may take a while for large files.")

#         # Split the audio file if it is too long
#         audio = AudioSegment.from_file(saved_file_path)
#         if len(audio) > 20 * 60 * 1000:
#             st.write("The audio file is too large and will be processed in chunks.")
#             parts = split_audio(saved_file_path)
#         else:
#             parts = [saved_file_path]

#         # Transcribe each part
#         transcription = ""
#         for part in parts:
#             part_transcription = transcribe_audio(part)
#             if part_transcription:
#                 transcription += part_transcription
#             os.remove(part)

#         # Display the transcription if successful
#         if transcription:
#             st.text_area("Transcription:", transcription, height=300)
#         else:
#             st.error("Transcription failed.")

#         # Cleanup the temporary file
#         os.remove(saved_file_path)
#     else:
#         st.error("Failed to save the file.")
# else:
#     st.info("Please upload an audio file.")
