import tempfile
import os
import shutil
import uuid
import requests
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from faster_whisper import WhisperModel

app = FastAPI(title="Pi-Optimized Async Whisper API with Webhooks")

jobs = {}

print("Loading optimized Whisper model...")
model = WhisperModel("base", device="cpu", compute_type="int8")
print("Model loaded successfully!")

# Updated Background Task with Webhook logic
def transcribe_background_task(job_id: str, file_path: str, webhook_url: str = None):
    jobs[job_id]["status"] = "processing"
    
    try:
        segments, info = model.transcribe(file_path, beam_size=5, language="en")
        full_text = "".join([segment.text for segment in segments])
        
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["text"] = full_text.strip()
        
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
            
        # --- WEBHOOK LOGIC ---
        if webhook_url:
            try:
                # Package the job data to send to the webhook
                payload = {"job_id": job_id, **jobs[job_id]}
                # Fire and forget. We use a short timeout so a bad webhook URL doesn't hang the thread.
                requests.post(webhook_url, json=payload, timeout=10)
                print(f"Successfully sent webhook for job {job_id}")
            except requests.exceptions.RequestException as e:
                print(f"Failed to send webhook for job {job_id}: {e}")

# Updated Endpoint to accept webhook_url
@app.post("/transcribe/")
async def upload_audio(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...),
    webhook_url: str = Form(None) # Optional form field
):
    if not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="File must be an audio format.")

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "pending"}

    fd, temp_file_path = tempfile.mkstemp(suffix=".wav")
    try:
        with os.fdopen(fd, 'wb') as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        raise HTTPException(status_code=500, detail="Failed to save file.")
    finally:
        file.file.close()

    # Pass the webhook_url into the background task
    background_tasks.add_task(transcribe_background_task, job_id, temp_file_path, webhook_url)
    
    return {"job_id": job_id, "status": "pending", "message": "Transcription started."}

@app.get("/status/{job_id}")
async def get_transcription_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job ID not found.")
    return jobs[job_id]
