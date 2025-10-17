import requests
import os
from tqdm import tqdm
import zipfile

def download_file(url, destination, chunk_size=8192):
    """
    Download large file with progress bar and resume capability
    """
    # Check if file already exists and get its size
    resume_byte_pos = 0
    if os.path.exists(destination):
        resume_byte_pos = os.path.getsize(destination)
        print(f"Resuming download from {resume_byte_pos / (1024**3):.2f} GB")
    
    # Set headers for resuming
    headers = {}
    if resume_byte_pos > 0:
        headers['Range'] = f'bytes={resume_byte_pos}-'
    
    # Start download
    response = requests.get(url, headers=headers, stream=True, allow_redirects=True)
    total_size = int(response.headers.get('content-length', 0)) + resume_byte_pos
    
    mode = 'ab' if resume_byte_pos > 0 else 'wb'
    
    with open(destination, mode) as f:
        with tqdm(
            total=total_size,
            initial=resume_byte_pos,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
            desc=os.path.basename(destination)
        ) as pbar:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))
    
    print(f"\nDownload complete! File size: {os.path.getsize(destination) / (1024**3):.2f} GB")
    return destination

def unzip_file(zip_path, extract_to):
    """
    Extract zip file with progress bar
    """
    print(f"\nExtracting {zip_path}...")
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # Get list of files
        file_list = zip_ref.namelist()
        
        # Extract with progress
        with tqdm(total=len(file_list), desc="Extracting files") as pbar:
            for file in file_list:
                zip_ref.extract(file, extract_to)
                pbar.update(1)
    
    print(f"Extraction complete! Files extracted to: {extract_to}")

if __name__ == "__main__":
    # Configuration
    URL = "https://storage.googleapis.com/magentadata/datasets/e-gmd/v1.0.0/e-gmd-v1.0.0.zip"
    DATASET_DIR = "AnNOTEator/dataset"
    ZIP_FILE = os.path.join(DATASET_DIR, "e-gmd-v1.0.0.zip")
    
    # Create directory
    os.makedirs(DATASET_DIR, exist_ok=True)
    
    print("=" * 70)
    print("  E-GMD Dataset Downloader")
    print("=" * 70)
    print(f"\nURL: {URL}")
    print(f"Destination: {ZIP_FILE}")
    print(f"Expected size: ~131 GB")
    print(f"\nThis will take a while depending on your internet speed.")
    print("You can safely interrupt and resume the download later.\n")
    
    # Download
    try:
        download_file(URL, ZIP_FILE)
        
        # Ask user if they want to extract now
        extract = input("\nDownload complete! Extract now? (y/n): ").lower()
        if extract == 'y':
            unzip_file(ZIP_FILE, DATASET_DIR)
            print("\nAll done! Dataset ready for use.")
        else:
            print("\nYou can extract later by running:")
            print(f"  Expand-Archive -Path '{ZIP_FILE}' -DestinationPath '{DATASET_DIR}'")
    
    except KeyboardInterrupt:
        print("\n\nDownload interrupted. Run this script again to resume.")
    except Exception as e:
        print(f"\nError: {e}")
        print("You can try running the script again to resume the download.")