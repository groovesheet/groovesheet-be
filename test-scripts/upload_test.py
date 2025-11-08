"""Simple upload script to test the API"""
import requests
import os

file_path = r"D:\Coding Files\GitHub\groovesheet\groovesheet-be\Nirvana - Smells Like Teen Spirit (Official Music Video).mp3"
api_url = "http://localhost:8080/api/v1/transcribe"

print(f"Uploading: {os.path.basename(file_path)}")
print(f"File size: {os.path.getsize(file_path) / (1024*1024):.2f} MB")

with open(file_path, 'rb') as f:
    files = {'file': (os.path.basename(file_path), f, 'audio/mpeg')}
    headers = {'Authorization': 'Bearer test-token'}
    
    response = requests.post(api_url, files=files, headers=headers)
    
if response.status_code == 200:
    data = response.json()
    print(f"\n✓ Upload successful!")
    print(f"Job ID: {data['job_id']}")
    print(f"Status: {data['status']}")
    
    # Save job ID
    with open('last-job-id.txt', 'w') as f:
        f.write(data['job_id'])
else:
    print(f"✗ Upload failed: {response.status_code}")
    print(response.text)
