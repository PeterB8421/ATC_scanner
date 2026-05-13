import tempfile
import os
import shutil
import uuid
import requests
import logging
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
import nemo.collections.asr as nemo_asr

app = FastAPI(title="Async Parakeet ASR API with Webhooks")

jobs = {}

# Path to NeMo model
MODEL_PATH = "/models/test.nemo"

# Pretrained model to use if local model is not available
PRETRAINED_MODEL_NAME = "nvidia/parakeet-rnnt-1.1b"

if os.path.exists(MODEL_PATH):
    print(f"Loading Parakeet model from {MODEL_PATH}...")
    model = nemo_asr.models.ASRModel.restore_from(MODEL_PATH)
else:
    print("Loading pretrained model.")
    model = nemo_asr.models.ASRModel.from_pretrained(model_name=PRETRAINED_MODEL_NAME)
print("Model loaded successfully!")


def transcribe_background_task(job_id: str, file_path: str, webhook_url: str = None):
    """ ASR background task """
    jobs[job_id]["status"] = "processing"
    
    try:
        transcriptions = model.transcribe(audio=[file_path])
        
        # Safely extract the first item from the returned data
        if isinstance(transcriptions, tuple):
            result = transcriptions[0][0]
        else:
            result = transcriptions[0]
            
        # Extract the text from the Hypothesis object
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
            
        if webhook_url:
            # Send transcript to webhook endpoint
            try:
                # Package the job data to send to the webhook
                payload = {"job_id": job_id, **jobs[job_id]}
                # Short timeout so a bad webhook URL doesn't hang the thread.
                requests.post(webhook_url, json=payload, timeout=10)
                print(f"Successfully sent webhook for job {job_id}")
            except requests.exceptions.RequestException as e:
                print(f"Failed to send webhook for job {job_id}: {e}")


@app.post("/transcribe/")
async def upload_audio(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...),
    webhook_url: str = Form(None)  # Optional form field for the webhook callback
):
    """ Endpoint to receive a new file to transcribe """
    if not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="File must be an audio format.")

    job_id = str(uuid.uuid4())
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


@app.get("/status/{job_id}")
async def get_transcription_status(job_id: str):
    """ Endpoint for polling, retruns job status """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job ID not found.")
        
    return jobs[job_id]
