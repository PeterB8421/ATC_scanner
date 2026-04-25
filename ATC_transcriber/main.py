import tempfile
import os
import shutil
import uuid
import requests  # 🌟 NEW: Needed to send the webhook
import logging
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
import nemo.collections.asr as nemo_asr

app = FastAPI(title="Async Parakeet ASR API with Webhooks")

jobs = {}

MODEL_PATH = "/models/parakeet-model.nemo"

print(f"Loading Parakeet model from {MODEL_PATH}...")
model = nemo_asr.models.ASRModel.restore_from(MODEL_PATH)
print("Model loaded successfully!")


# 2. The Background Task Function
def transcribe_background_task(job_id: str, file_path: str, webhook_url: str = None):
    jobs[job_id]["status"] = "processing"
    
    try:
        transcriptions = model.transcribe(audio=[file_path])
        
        # 1. Safely extract the first item from the returned data
        if isinstance(transcriptions, tuple):
            result = transcriptions[0][0]
        else:
            result = transcriptions[0]
            
        # 2. 🌟 THE NEW FIX: Extract the text from the Hypothesis object
        if hasattr(result, 'text'):
            full_text = result.text
        else:
            # Fallback just in case a future version returns a raw string
            full_text = str(result)
            
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["text"] = full_text.strip()
        
    except Exception as e:
        logging.error(f'Job failed, error: {e}')
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        
    finally:
        # Clean up the file first so we don't leak storage if the webhook hangs
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


# 3. Endpoint 1: Upload the file (Now accepts an optional webhook_url)
@app.post("/transcribe/")
async def upload_audio(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...),
    webhook_url: str = Form(None)  # 🌟 NEW: Optional form field for the callback
):
    if not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="File must be an audio format.")

    job_id = str(uuid.uuid4())
    # Store the webhook URL in our job state just in case we need to debug it later
    jobs[job_id] = {"status": "pending", "webhook_url": webhook_url}

    fd, temp_file_path = tempfile.mkstemp(suffix=".wav")
    try:
        with os.fdopen(fd, 'wb') as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        raise HTTPException(status_code=500, detail="Failed to save file.")
    finally:
        file.file.close()

    # Pass the webhook URL into the background task
    background_tasks.add_task(transcribe_background_task, job_id, temp_file_path, webhook_url)
    
    return {
        "job_id": job_id, 
        "status": "pending", 
        "message": "Transcription started.",
        "webhook_url": webhook_url
    }


# 4. Endpoint 2: The Polling fallback (Keep this just in case!)
@app.get("/status/{job_id}")
async def get_transcription_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job ID not found.")
        
    return jobs[job_id]
