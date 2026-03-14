import requests
import time
import sys

# Change this if your Pi is on a different IP address
API_BASE_URL = "http://localhost:11000" 

def transcribe_audio(file_path: str):
    print(f"Uploading '{file_path}' to the API...")
    
    # 1. Send the POST request with the audio file
    upload_url = f"{API_BASE_URL}/transcribe/"
    
    try:
        with open(file_path, "rb") as audio_file:
            # We must send it as multipart/form-data, matching FastAPI's UploadFile
            files = {"file": (file_path, audio_file, "audio/wav")}
            response = requests.post(upload_url, files=files)
            response.raise_for_status() # Check for HTTP errors
    except FileNotFoundError:
        print(f"Error: Could not find the file '{file_path}'.")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to the API: {e}")
        sys.exit(1)

    # 2. Extract the Job ID
    data = response.json()
    job_id = data.get("job_id")
    
    if not job_id:
        print("Error: API did not return a Job ID.")
        sys.exit(1)

    print(f"Success! Job ID received: {job_id}")
    print("-" * 30)

    # 3. Poll the GET request every 5 seconds
    status_url = f"{API_BASE_URL}/status/{job_id}"
    
    while True:
        try:
            status_response = requests.get(status_url)
            status_response.raise_for_status()
            status_data = status_response.json()
            
            current_status = status_data.get("status")
            
            if current_status == "completed":
                print("\n✅ Transcription Complete!")
                print(f"Text: {status_data.get('text')}")
                break
                
            elif current_status == "failed":
                print(f"\n❌ Transcription Failed!")
                print(f"Error details: {status_data.get('error', 'Unknown error')}")
                break
                
            else:
                # It is either 'pending' or 'processing'
                print(f"[{time.strftime('%X')}] Status: {current_status}... waiting 5 seconds.")
                time.sleep(5)
                
        except requests.exceptions.RequestException as e:
            print(f"\nError checking status: {e}")
            print("Retrying in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    # Replace with the actual name of your audio file
    TARGET_FILE = "test_audio.wav" 
    transcribe_audio(TARGET_FILE)
