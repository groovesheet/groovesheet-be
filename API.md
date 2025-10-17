# DrumScore Backend API Documentation

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication
Currently, no authentication is required. For production, implement API key authentication.

---

## Endpoints

### 1. Health Check

#### `GET /health`

Check server health and readiness.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "models_loaded": true,
  "gpu_available": true,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**Status Codes:**
- `200 OK`: Server is healthy
- `503 Service Unavailable`: Server is initializing

---

### 2. Upload Audio for Transcription

#### `POST /transcribe`

Upload an audio file to start drum transcription.

**Content-Type:** `multipart/form-data`

**Parameters:**
- `audio_file` (required): Audio file (MP3, WAV)
  - Max size: 100MB
  - Supported formats: audio/mpeg, audio/wav

**Example (cURL):**
```bash
curl -X POST "http://localhost:8000/api/v1/transcribe" \
  -F "audio_file=@/path/to/song.mp3"
```

**Example (Python):**
```python
import requests

with open('song.mp3', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/v1/transcribe',
        files={'audio_file': f}
    )
    
job = response.json()
print(f"Job ID: {job['job_id']}")
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "filename": "song.mp3",
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z",
  "message": "Job created",
  "progress": 0
}
```

**Status Codes:**
- `200 OK`: File uploaded successfully
- `400 Bad Request`: Invalid file format or missing file
- `413 Payload Too Large`: File exceeds size limit
- `500 Internal Server Error`: Server error

---

### 3. Check Job Status

#### `GET /status/{job_id}`

Get the current status of a transcription job.

**Path Parameters:**
- `job_id` (required): Unique job identifier from upload response

**Example (cURL):**
```bash
curl "http://localhost:8000/api/v1/status/550e8400-e29b-41d4-a716-446655440000"
```

**Example (Python):**
```python
import requests

job_id = "550e8400-e29b-41d4-a716-446655440000"
response = requests.get(f'http://localhost:8000/api/v1/status/{job_id}')
status = response.json()
print(f"Progress: {status['progress']}%")
```

**Response (Processing):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "transcribing",
  "progress": 65,
  "message": "Transcribing drum notation..."
}
```

**Response (Completed):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 100,
  "message": "Processing completed in 125.34s",
  "result_url": "/api/v1/download/550e8400-e29b-41d4-a716-446655440000/pdf",
  "midi_url": "/api/v1/download/550e8400-e29b-41d4-a716-446655440000/midi",
  "drum_audio_url": "/api/v1/download/550e8400-e29b-41d4-a716-446655440000/audio"
}
```

**Status Values:**
- `pending`: Job is queued
- `separating`: Separating drum track from audio
- `transcribing`: Transcribing drums to MIDI
- `generating_sheet`: Generating PDF sheet music
- `completed`: Processing finished successfully
- `failed`: Processing failed

**Status Codes:**
- `200 OK`: Status retrieved successfully
- `404 Not Found`: Job ID not found
- `500 Internal Server Error`: Server error

---

### 4. Download PDF Sheet Music

#### `GET /download/{job_id}/pdf`

Download the generated PDF sheet music.

**Path Parameters:**
- `job_id` (required): Unique job identifier

**Example (cURL):**
```bash
curl -O "http://localhost:8000/api/v1/download/550e8400-e29b-41d4-a716-446655440000/pdf"
```

**Example (Python):**
```python
import requests

job_id = "550e8400-e29b-41d4-a716-446655440000"
response = requests.get(f'http://localhost:8000/api/v1/download/{job_id}/pdf')

with open('drum_sheet.pdf', 'wb') as f:
    f.write(response.content)
```

**Response:**
- Binary PDF file
- Content-Type: `application/pdf`
- Filename: `drum_sheet_{job_id}.pdf`

**Status Codes:**
- `200 OK`: File downloaded successfully
- `400 Bad Request`: Job not completed yet
- `404 Not Found`: Job or file not found
- `500 Internal Server Error`: Server error

---

### 5. Download MIDI File

#### `GET /download/{job_id}/midi`

Download the transcribed MIDI file.

**Path Parameters:**
- `job_id` (required): Unique job identifier

**Example (cURL):**
```bash
curl -O "http://localhost:8000/api/v1/download/550e8400-e29b-41d4-a716-446655440000/midi"
```

**Example (Python):**
```python
import requests

job_id = "550e8400-e29b-41d4-a716-446655440000"
response = requests.get(f'http://localhost:8000/api/v1/download/{job_id}/midi')

with open('drums.mid', 'wb') as f:
    f.write(response.content)
```

**Response:**
- Binary MIDI file
- Content-Type: `audio/midi`
- Filename: `drums_{job_id}.mid`

**Status Codes:**
- `200 OK`: File downloaded successfully
- `400 Bad Request`: Job not completed yet
- `404 Not Found`: Job or file not found
- `500 Internal Server Error`: Server error

---

### 6. Download Separated Drum Audio

#### `GET /download/{job_id}/audio`

Download the separated drum audio track.

**Path Parameters:**
- `job_id` (required): Unique job identifier

**Example (cURL):**
```bash
curl -O "http://localhost:8000/api/v1/download/550e8400-e29b-41d4-a716-446655440000/audio"
```

**Example (Python):**
```python
import requests

job_id = "550e8400-e29b-41d4-a716-446655440000"
response = requests.get(f'http://localhost:8000/api/v1/download/{job_id}/audio')

with open('drums.wav', 'wb') as f:
    f.write(response.content)
```

**Response:**
- Binary WAV file
- Content-Type: `audio/wav`
- Filename: `drums_{job_id}.wav`

**Status Codes:**
- `200 OK`: File downloaded successfully
- `400 Bad Request`: Job not completed yet
- `404 Not Found`: Job or file not found
- `500 Internal Server Error`: Server error

---

## Complete Workflow Example

### JavaScript (Frontend Integration)

```javascript
async function transcribeDrums(audioFile) {
    // 1. Upload file
    const formData = new FormData();
    formData.append('audio_file', audioFile);
    
    const uploadResponse = await fetch('http://localhost:8000/api/v1/transcribe', {
        method: 'POST',
        body: formData
    });
    
    const job = await uploadResponse.json();
    const jobId = job.job_id;
    
    // 2. Poll for status
    let status = 'pending';
    while (status !== 'completed' && status !== 'failed') {
        await new Promise(resolve => setTimeout(resolve, 5000)); // Wait 5 seconds
        
        const statusResponse = await fetch(
            `http://localhost:8000/api/v1/status/${jobId}`
        );
        const statusData = await statusResponse.json();
        
        status = statusData.status;
        console.log(`Progress: ${statusData.progress}%`);
        
        if (status === 'failed') {
            throw new Error(statusData.message);
        }
    }
    
    // 3. Download results
    const pdfUrl = `http://localhost:8000/api/v1/download/${jobId}/pdf`;
    const midiUrl = `http://localhost:8000/api/v1/download/${jobId}/midi`;
    const audioUrl = `http://localhost:8000/api/v1/download/${jobId}/audio`;
    
    return { pdfUrl, midiUrl, audioUrl };
}

// Usage
const fileInput = document.getElementById('audio-file');
fileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    try {
        const results = await transcribeDrums(file);
        console.log('Download URLs:', results);
    } catch (error) {
        console.error('Transcription failed:', error);
    }
});
```

### Python (Complete Example)

```python
import requests
import time

def transcribe_drums(audio_path, output_dir='results'):
    """
    Complete workflow: upload -> monitor -> download
    """
    base_url = 'http://localhost:8000/api/v1'
    
    # 1. Upload file
    print(f"Uploading {audio_path}...")
    with open(audio_path, 'rb') as f:
        response = requests.post(
            f'{base_url}/transcribe',
            files={'audio_file': f}
        )
    response.raise_for_status()
    
    job = response.json()
    job_id = job['job_id']
    print(f"Job created: {job_id}")
    
    # 2. Monitor progress
    print("\nMonitoring progress...")
    while True:
        response = requests.get(f'{base_url}/status/{job_id}')
        response.raise_for_status()
        
        status_data = response.json()
        status = status_data['status']
        progress = status_data['progress']
        message = status_data['message']
        
        print(f"[{progress}%] {status}: {message}")
        
        if status == 'completed':
            print("\n✓ Processing complete!")
            break
        elif status == 'failed':
            raise Exception(f"Processing failed: {message}")
        
        time.sleep(5)  # Wait 5 seconds before next check
    
    # 3. Download results
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    files = {
        'pdf': f'{base_url}/download/{job_id}/pdf',
        'midi': f'{base_url}/download/{job_id}/midi',
        'audio': f'{base_url}/download/{job_id}/audio'
    }
    
    downloaded_files = {}
    for file_type, url in files.items():
        print(f"Downloading {file_type}...")
        response = requests.get(url)
        response.raise_for_status()
        
        # Save file
        ext = {'pdf': '.pdf', 'midi': '.mid', 'audio': '.wav'}[file_type]
        output_path = os.path.join(output_dir, f'drums_{file_type}{ext}')
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        downloaded_files[file_type] = output_path
        print(f"  Saved to: {output_path}")
    
    return downloaded_files

# Usage
if __name__ == '__main__':
    results = transcribe_drums('my_song.mp3')
    print("\nResults:")
    for file_type, path in results.items():
        print(f"  {file_type}: {path}")
```

---

## Error Handling

### Error Response Format

```json
{
  "error": "ProcessingError",
  "message": "Failed to process audio file",
  "details": {
    "step": "separation",
    "reason": "Invalid audio format"
  }
}
```

### Common Errors

| Error Code | Error Type | Description | Solution |
|------------|------------|-------------|----------|
| 400 | ValidationError | Invalid file format | Use MP3 or WAV |
| 413 | PayloadTooLarge | File too large | Compress or split file |
| 404 | NotFound | Job ID not found | Check job ID |
| 503 | ServiceUnavailable | Server not ready | Wait and retry |
| 500 | InternalError | Server error | Contact support |

---

## Rate Limiting

- Max concurrent jobs: 3 (configurable)
- No request rate limit by default
- For production, implement rate limiting per IP/API key

---

## Performance Tips

1. **Optimize file size**: Compress audio before upload
2. **Use appropriate format**: MP3 for smaller files, WAV for quality
3. **Poll efficiently**: Check status every 5-10 seconds
4. **Handle timeouts**: Set reasonable timeouts on client side
5. **GPU acceleration**: Use GPU for 3-5x faster processing

---

## Interactive Documentation

Visit `http://localhost:8000/docs` for interactive Swagger UI documentation where you can:
- Test all endpoints
- See request/response schemas
- Try example requests
- Download OpenAPI specification

---

Built with FastAPI and ❤️
