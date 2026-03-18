import json
import logging
import asyncio
import httpx
import requests
import aiofiles
import threading
from BaseProcessor import BaseProcessor, register_plugin
from asgiref.sync import sync_to_async


FAIL_TEXT = "[Transcription failed]"


@register_plugin("whisper_asr")
class WhisperASR(BaseProcessor):
    def process(self, file_path: str):
        try:
            with open(file_path, "rb") as audio_file:
                # We must send it as multipart/form-data, matching FastAPI's UploadFile
                files = {"file": (file_path, audio_file, "audio/wav")}
                response = requests.post(self.config["url"] + "/transcribe/", files=files)
                response.raise_for_status()  # Check for HTTP errors
        except FileNotFoundError:
            print(f"Error: File not found: '{file_path}'.")
            return
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to the API: {e}")
            return

        data = response.json()
        job_id = data.get("job_id")

        if job_id:
            polling_thread = threading.Thread(
                target=lambda: asyncio.run(self.poll_job_async(job_id, file_path))
            )
            polling_thread.start()
        return

    async def poll_job_async(self, job_id, file_path: str):
        base_url = self.config["url"]  # Base URL of ASR API
        status_url = f"{base_url}/status/{job_id}"  # URL to get job status

        max_attempts = 300  # Timeout after 5 minutes
        attempts = 0

        # Make an async connection to the API and poll the status
        async with httpx.AsyncClient() as client:
            while attempts < max_attempts:
                attempts += 1
                try:
                    response = await client.get(status_url)
                    response.raise_for_status()
                    data = response.json()  # Job status data

                    status = data.get("status")
                    if status in ["completed", "failed"]:
                        if status == "completed":
                            # If transcript is completed, save the text to file metadata
                            text = data.get("text")
                        else:
                            # If transcription failed, save the FAIL_TEXT
                            text = FAIL_TEXT
                        await self._update_json_transcript(file_path, text)
                        await self._update_database_transcript(file_path, text)
                        return
                except httpx.RequestError as e:
                    logging.error(f"Unable to connect to ASR API: {e}")
                    await self._update_json_transcript(file_path, FAIL_TEXT)
                    await self._update_database_transcript(file_path, FAIL_TEXT)

                await asyncio.sleep(1)
            logging.error(f"ASR API timed out for {file_path}")
            await self._update_json_transcript(file_path, FAIL_TEXT)
            await self._update_database_transcript(file_path, FAIL_TEXT)

    async def _update_json_transcript(self, file_path: str, text: str):
        """Update metadata JSON file"""
        json_path = file_path.replace(".wav", ".json")
        try:
            async with aiofiles.open(json_path, mode="r") as json_file:
                content = await json_file.read()
                metadata = json.loads(content)

            metadata['transcript'] = text

            async with aiofiles.open(json_path, mode="w") as json_file:
                updated_content = json.dumps(metadata, indent=2, sort_keys=True)
                await json_file.write(updated_content)

        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Failed to async update JSON for {file_path}: {e}")

    @sync_to_async
    def _update_database_transcript(self, file_path: str, text: str):
        """Update text in database"""
        from django.db import close_old_connections
        close_old_connections()
        try:
            from mainApp.models import Recording
            rows_updated = Recording.objects.filter(file_path=file_path).update(transcript=text)

            if rows_updated == 0:
                logging.warning(f"No database record found for '{file_path}'.")

        except Exception as e:
            logging.error(f"Failed to update database entry for {file_path}: {e}")
        finally:
            close_old_connections()
