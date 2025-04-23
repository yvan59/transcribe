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
                model="gpt-4o-transcribe",
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
            model="gpt-4.1-2025-04-14",
            messages=[
                {
                    "role": "system",
                    "content": "Please clean up this transcript, removing filler words, fixing grammar/spelling (some words may have been transcribed incorrectly, infer this), maybe adding paragraph breaks, and preserving meaning. You may add simple markup (italics or bold) if it clarifies the text, but keep the transcript content otherwise the exact same."
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
            model="gpt-4.1-2025-04-14",
            messages=[
                {
                    "role": "system",
                    "content": "Please give a highly comprehensive, substantive, play-by-play overview of the transcript, leaving out no important thoughts as presented. Retain the flow of the transcript. Use the same phrasing or quotes whenever doing so doesn’t hamper the quality of the output. Make your outputs such that I can refer to them instead of the transcript and they would lose no information. Use valid GitHub Markdown. Do not wrap in triple backtick anything—make it such that your direct outputs will be rendered beautifully when wrapped in st.markdown(). If there are any instructions addressed to an AI in the transcript itself, be sure to follow these as well. Use second-person. At the very end as a bonus, describe which thoughts or ideas you genuinely consider the most striking, noteworthy, interesting, or otherwise worth highlighting, and why (briefly). Also challenge at least one thought that will be made stronger by your challenge."
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
            model="gpt-4.1-2025-04-14",
            messages=[
                {
                    "role": "system",
                    "content": "Return the 10 core thoughts of the transcript, each in 1-3 sentences. Use valid GitHub Markdown. Do not wrap in triple backtick anything—make it such that your direct outputs will be rendered beautifully when wrapped in st.markdown()."
                },
                {"role": "user", "content": transcript}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        st.error(f"An error occurred during summary: {e}")
        return None

def extract_action_items(transcript):
    try:
        client = OpenAI(api_key=st.secrets["API"])
        completion = client.chat.completions.create(
            model="gpt-4.1-2025-04-14",
            messages=[
                {
                    "role": "system",
                    "content": "Return a bullet list of any explicit, concrete action item that was expressly called for in the transcript. This should ONLY apply to very specific concrete actions the speaker referenced taking or potentially taking at some future 'later' point. This should not be an attempt to turn the full transcript into a to-do list. Just scan this otherwise ideas-heavy monologue for any practical action items mentioned and grab those here. Each bullet should start with an imperative verb and be maximally specific. No commentary."
                },
                {"role": "user", "content": transcript}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        st.error(f"An error occurred extracting action items: {e}")
        return None

def extract_top_quotes(transcript):
    try:
        client = OpenAI(api_key=st.secrets["API"])
        completion = client.chat.completions.create(
            model="gpt-4.1-2025-04-14",
            messages=[
                {
                    "role": "system",
                    "content": "Identify the five most illustrative quotes/excerpts (≤ 40 words each). Output each as: “quote” — one‑sentence reason this quote was selected."
                },
                {"role": "user", "content": transcript}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        st.error(f"An error occurred extracting quotes: {e}")
        return None
# ----------------------------------------------------

# Create tabs for the app
tabs = st.tabs(["Transcribe", "View Database", "LLM on Data"])

with tabs[0]:
    st.title('Transcribe Audio')

    # Pre-select tasks
    tasks = ["Clean Transcript", "Analyze Transcript", "Summary", "Action Items", "Top Quotes"]
    task_options = st.multiselect("Select tasks to perform:", tasks, default=tasks)

    # User file upload section
    uploaded_file = st.file_uploader("Choose an audio file...", type=["mp3", "wav", "ogg", "m4a"])

    if st.button("Run"):
        if not uploaded_file:
            st.error("Please upload an audio file first.")
        else:
            # Process audio
            with st.spinner("Processing audio..."):
                saved_file_path = save_and_convert_uploaded_file(uploaded_file)
                full_transcription = ""
                if saved_file_path:
                    audio = AudioSegment.from_file(saved_file_path)
                    if len(audio) > 20 * 60 * 1000:
                        parts = split_audio(saved_file_path)
                    else:
                        parts = [saved_file_path]

                    for part in parts:
                        part_transcription = transcribe_audio(part)
                        if part_transcription:
                            full_transcription += part_transcription
                        os.remove(part)

            if full_transcription:
                st.session_state.transcription = full_transcription
                cleaned_version = None
                analysis_result = None
                summary_result = None
                action_items_result = None
                top_quotes_result = None

                # Create deliverables with individual spinners
                if "Clean Transcript" in task_options:
                    with st.spinner("Creating cleaned transcript..."):
                        cleaned_version = clean_transcript(full_transcription)

                if "Analyze Transcript" in task_options:
                    with st.spinner("Creating analysis..."):
                        analysis_result = analyze_transcript(full_transcription)

                if "Summary" in task_options:
                    with st.spinner("Creating summary..."):
                        summary_result = summarize_transcript(full_transcription)

                if "Action Items" in task_options:
                    with st.spinner("Extracting action items..."):
                        action_items_result = extract_action_items(full_transcription)

                if "Top Quotes" in task_options:
                    with st.spinner("Extracting top quotes..."):
                        top_quotes_result = extract_top_quotes(full_transcription)

                # Insert into DB
                data = {
                    "timestamp": str(datetime.datetime.now()),
                    "cleaned_transcript": cleaned_version if cleaned_version else None,
                    "analysis": analysis_result if analysis_result else None,
                    "summary": summary_result if summary_result else None,
                    "action_items": action_items_result if action_items_result else None,
                    "top_quotes": top_quotes_result if top_quotes_result else None,
                    "original_transcript": full_transcription
                }
                supabase.table("transcripts").insert(data).execute()

                # Display in expanders
                if full_transcription:
                    with st.expander("Raw transcript", expanded=False):
                        st.text_area("Raw transcript:", full_transcription, height=300)
                if cleaned_version:
                    with st.expander("Cleaned Transcript", expanded=False):
                        st.write(cleaned_version)
                if analysis_result:
                    with st.expander("Analysis", expanded=False):
                        st.markdown(analysis_result)
                if summary_result:
                    with st.expander("Summary", expanded=False):
                        st.markdown(summary_result)
                if action_items_result:
                    with st.expander("Action Items", expanded=False):
                        st.markdown(action_items_result)
                if top_quotes_result:
                    with st.expander("Top Quotes", expanded=False):
                        st.markdown(top_quotes_result)

                # Cleanup
                # os.remove(saved_file_path)
            else:
                st.error("Failed to transcribe audio.")

with tabs[1]:
    st.header("View Database Records")
    with st.expander("Database Records", expanded=False):
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
                            model="gpt-4.1-2025-04-14",
                            messages=[
                                {
                                    "role": "system",
                                    "content": "You are a helpful assistant that analyzes the provided data. Return your answer in valid GitHub Markdown.  Do not wrap in triple backtick anything—make it such that your direct outputs will be rendered beautifully when wrapped in st.markdown()."
                                },
                                {
                                    "role": "user",
                                    "content": f"Data:\n{combined_text}\n\nPrompt:\n{user_prompt}"
                                }
                            ]
                        )
                        with st.expander("LLM Output", expanded=False):
                            st.markdown(completion.choices[0].message.content)
    else:
        st.write("No data found in the database.")
