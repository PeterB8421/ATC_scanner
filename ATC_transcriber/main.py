import tempfile
import os
import shutil
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from faster_whisper import WhisperModel

app = FastAPI(title="Pi-Optimized Async Whisper API")

# 1. In-memory storage for our jobs
# Note: If you restart the container, this memory is cleared.
jobs = {}

print("Loading optimized Whisper model...")
model = WhisperModel("base", device="cpu", compute_type="int8")
print("Model loaded successfully!")


# 2. The Background Task Function
# This runs invisibly after the user gets their response.
def transcribe_background_task(job_id: str, file_path: str):
    jobs[job_id]["status"] = "processing"
    
    try:
        # Hardcoded to English for speed
        segments, info = model.transcribe(file_path, beam_size=5, language="en")
        full_text = "".join([segment.text for segment in segments])
        
        # Save the result to our dictionary
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["text"] = full_text.strip()
        
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        
    finally:
        # Crucial: The background task must clean up the file when it finishes
        if os.path.exists(file_path):
            os.remove(file_path)


# 3. Endpoint 1: Upload the file and get a Job ID
@app.post("/transcribe/")
async def upload_audio(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="File must be an audio format.")

    # Generate a unique ID for this transcription job
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "pending"}

    # We must save the file manually without a 'with' block, 
    # otherwise it deletes itself before the background task can read it!
    fd, temp_file_path = tempfile.mkstemp(suffix=".wav")
    try:
        with os.fdopen(fd, 'wb') as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        raise HTTPException(status_code=500, detail="Failed to save file.")
    finally:
        file.file.close()

    # Hand the job off to FastAPI's background queue
    background_tasks.add_task(transcribe_background_task, job_id, temp_file_path)
    
    # Return instantly! No timeouts.
    return {"job_id": job_id, "status": "pending", "message": "Transcription started."}


# 4. Endpoint 2: Check the status of the job
@app.get("/status/{job_id}")
async def get_transcription_status(job_id: str):
    # Check if the job exists
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job ID not found.")
        
    # Return whatever the current status is (pending, processing, completed, or failed)
    return jobs[job_id]
