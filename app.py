import streamlit as st
import os
from pathlib import Path
from openai import OpenAI
from pydub import AudioSegment
from supabase import create_client, Client
import datetime

# --- Extremely Simple Login Credential Check ---
password_input = st.text_input("Enter password:", type="password")
if st.button("Login"):
    if password_input == st.secrets["password"]:
        st.session_state["logged_in"] = True
    else:
        st.error("Invalid password")

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.stop()
# ----------------------------------------------

# --- Connect to Supabase ---
supabase_url = st.secrets["SUPABASE_URL"]
supabase_key = st.secrets["SUPABASE_SERVICE_KEY"]
supabase: Client = create_client(supabase_url, supabase_key)
# ---------------------------

system_message = """
You will be presented with a stream of consciousness transcript. Your job is to regurgitate the entire transcript and leave out NONE of the key ideas and tone and cadence, in the exact language of the original 
transcript whenever possible and present the content in the same order and style as the transcript. However, the text you return should be a minimally cleaned up version of the transcript and be 'all meat, no fat.' This does not mean to leave out ANY self-contained thoughts
(do not leave out any), but rather to present the SAME thoughts in a slightly cleaner format so it doesn't read like a rambling stream of consciousness and instead is a cleaned up version of the same thing.
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

# -------- New Functions for Additional Tasks --------
def clean_transcript(transcript):
    try:
        client = OpenAI(api_key=st.secrets["API"])
        completion = client.chat.completions.create(
            model="o3-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Please clean up this transcript, removing filler words, fixing grammar/spelling, and preserving meaning. You may add simple markup (italics or bold) if it clarifies the text, but keep the transcript content otherwise the same."
                },
                {"role": "user", "content": transcript}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        st.error(f"An error occurred during cleaning: {e}")
        return None

def analyze_transcript(transcript):
    try:
        client = OpenAI(api_key=st.secrets["API"])
        completion = client.chat.completions.create(
            model="o1",
            messages=[
                {
                    "role": "system",
                    "content": "Please give a highly comprehensive substantive overview of the transcript, leaving out no important thoughts as presented. Use the same phrasing or quotes whenever doing so doesn’t hamper the quality of the output. Make your outputs such that I can refer to them instead of the transcript and they would lose no information. If there are any instructions to you in the transcript itself, be sure to follow these as well. Use second-person. At the very end as a bonus, describe which thoughts or ideas you genuinely consider the most striking, noteworthy, interesting, or otherwise worth highlighting, and why (briefly). Also challenge at least one thought that will be made stronger by your challenge."
                },
                {"role": "user", "content": transcript}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        st.error(f"An error occurred during analysis: {e}")
        return None

def summarize_transcript(transcript):
    try:
        client = OpenAI(api_key=st.secrets["API"])
        completion = client.chat.completions.create(
            model="o3-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Return the 10 core thoughts of the transcript, each in 1-3 sentences."
                },
                {"role": "user", "content": transcript}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        st.error(f"An error occurred during summary: {e}")
        return None
# ----------------------------------------------------

# Create tabs for the app
tabs = st.tabs(["Transcribe", "View Database", "LLM on Data"])

with tabs[0]:
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
                    st.session_state.processed_info = process_transcript(st.session_state.transcription)
                st.write("**Processed Transcript:**", st.session_state.processed_info)
            else:
                st.error("Transcription failed.")

            # Cleanup the temporary file
            # os.remove(saved_file_path)
        else:
            st.error("Failed to save the file.")
    else:
        st.info("Please upload an audio file.")

    # ----- Multi-select for additional tasks -----
    st.write("### Additional Analysis Options")
    task_options = st.multiselect(
        "Select tasks to perform",
        ["Clean Transcript", "Analyze Transcript", "Summary"]
    )
    if st.button("Run Selected Tasks"):
        cleaned_version = None
        analysis_result = None
        summary_result = None

        if "Clean Transcript" in task_options and st.session_state.transcription:
            cleaned_version = clean_transcript(st.session_state.transcription)

        if "Analyze Transcript" in task_options and st.session_state.transcription:
            analysis_result = analyze_transcript(st.session_state.transcription)

        if "Summary" in task_options and st.session_state.transcription:
            summary_result = summarize_transcript(st.session_state.transcription)

        if cleaned_version:
            st.write("**Cleaned Transcript:**", cleaned_version)
        if analysis_result:
            st.write("**Analysis:**", analysis_result)
        if summary_result:
            st.write("**Summary:**", summary_result)

        # If any new data was generated, store in the database
        if cleaned_version or analysis_result or summary_result:
            data = {
                "timestamp": str(datetime.datetime.now()),
                "cleaned_transcript": cleaned_version if cleaned_version else None,
                "analysis": analysis_result if analysis_result else None,
                "summary": summary_result if summary_result else None,
                "original_transcript": st.session_state.transcription
            }
            supabase.table("transcripts").insert(data).execute()

with tabs[1]:
    st.header("View Database Records")
    result = supabase.table("transcripts").select("*").execute()
    if result.data:
        st.write(result.data)
    else:
        st.write("No records found.")

with tabs[2]:
    st.header("LLM on Data")
    result = supabase.table("transcripts").select("*").execute()
    records = result.data if result.data else []
    if records:
        timestamps = [r["timestamp"] for r in records]
        selected_timestamps = st.multiselect("Select timestamps to include:", timestamps)

        if selected_timestamps:
            filtered_records = [r for r in records if r["timestamp"] in selected_timestamps]
            if filtered_records:
                columns = list(filtered_records[0].keys())
                selected_columns = st.multiselect("Select columns to pass to LLM:", columns)

                user_prompt = st.text_area("Enter prompt for the LLM:", "")
                if st.button("Run LLM on selected data"):
                    combined_text = ""
                    for rec in filtered_records:
                        for col in selected_columns:
                            combined_text += f"{col}: {rec.get(col, '')}\n"

                    if combined_text and user_prompt:
                        client = OpenAI(api_key=st.secrets["API"])
                        completion = client.chat.completions.create(
                            model="o3-mini",
                            messages=[
                                {
                                    "role": "system",
                                    "content": "You are a helpful assistant that analyzes the provided data."
                                },
                                {
                                    "role": "user",
                                    "content": f"Data:\n{combined_text}\n\nPrompt:\n{user_prompt}"
                                }
                            ]
                        )
                        st.write("**LLM Output:**", completion.choices[0].message.content)
    else:
        st.write("No data found in the database.")
