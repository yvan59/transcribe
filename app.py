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

# Initialize session state
if 'transcription' not in st.session_state:
    st.session_state.transcription = ""

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

    # Pre-select tasks
    tasks = ["Clean Transcript", "Analyze Transcript", "Summary"]
    task_options = st.multiselect("Select tasks to perform:", tasks, default=tasks)

    # User file upload section
    uploaded_file = st.file_uploader("Choose an audio file...", type=["mp3", "wav", "ogg", "m4a"])

    if st.button("Run"):
        if not uploaded_file:
            st.error("Please upload an audio file first.")
        else:
            with st.spinner("Processing audio..."):
                saved_file_path = save_and_convert_uploaded_file(uploaded_file)
                if saved_file_path:
                    # Transcribe in chunks if needed
                    audio = AudioSegment.from_file(saved_file_path)
                    if len(audio) > 20 * 60 * 1000:
                        parts = split_audio(saved_file_path)
                    else:
                        parts = [saved_file_path]

                    full_transcription = ""
                    for part in parts:
                        part_transcription = transcribe_audio(part)
                        if part_transcription:
                            full_transcription += part_transcription
                        os.remove(part)

                    st.session_state.transcription = full_transcription

                    # Run selected tasks
                    cleaned_version = None
                    analysis_result = None
                    summary_result = None

                    if "Clean Transcript" in task_options:
                        cleaned_version = clean_transcript(full_transcription)

                    if "Analyze Transcript" in task_options:
                        analysis_result = analyze_transcript(full_transcription)

                    if "Summary" in task_options:
                        summary_result = summarize_transcript(full_transcription)

                    # Insert into DB
                    data = {
                        "timestamp": str(datetime.datetime.now()),
                        "cleaned_transcript": cleaned_version if cleaned_version else None,
                        "analysis": analysis_result if analysis_result else None,
                        "summary": summary_result if summary_result else None,
                        "original_transcript": full_transcription
                    }
                    supabase.table("transcripts").insert(data).execute()

                    # Display results
                    if full_transcription:
                        st.write("### Original Transcript")
                        st.text_area("Raw transcript:", full_transcription, height=300)
                    if cleaned_version:
                        st.write("### Cleaned Transcript")
                        st.write(cleaned_version)
                    if analysis_result:
                        st.write("### Analysis")
                        st.write(analysis_result)
                    if summary_result:
                        st.write("### Summary")
                        st.write(summary_result)

                    # Cleanup
                    # os.remove(saved_file_path)
                else:
                    st.error("Failed to save file.")

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
