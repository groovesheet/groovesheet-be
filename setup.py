"""
Setup script for DrumScore Backend
"""
import os
import sys
import subprocess
import platform

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60 + "\n")

def run_command(command, description):
    """Run a shell command with error handling"""
    print(f"➤ {description}...")
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                command,
                shell=True,
                check=True,
                capture_output=True,
                text=True
            )
        else:
            result = subprocess.run(
                command.split(),
                check=True,
                capture_output=True,
                text=True
            )
        print(f"  ✓ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ {description} failed: {e}")
        return False

def check_python_version():
    """Check Python version"""
    print_header("Checking Python Version")
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major != 3 or version.minor != 8:
        print("⚠ Warning: This project is designed for Python 3.8")
        print(f"  You are using Python {version.major}.{version.minor}")
        response = input("  Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    else:
        print("✓ Python version is correct")

def check_system_dependencies():
    """Check for required system dependencies"""
    print_header("Checking System Dependencies")
    
    dependencies = {
        "ffmpeg": "ffmpeg -version",
        "git": "git --version"
    }
    
    all_present = True
    for name, command in dependencies.items():
        try:
            subprocess.run(
                command.split(),
                check=True,
                capture_output=True
            )
            print(f"✓ {name} is installed")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"✗ {name} is NOT installed")
            all_present = False
    
    if not all_present:
        print("\n⚠ Please install missing dependencies:")
        print("  - FFmpeg: https://ffmpeg.org/download.html")
        response = input("\nContinue without missing dependencies? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)

def create_directories():
    """Create necessary directories"""
    print_header("Creating Directories")
    
    dirs = [
        "backend/uploads",
        "backend/temp",
        "backend/outputs",
        "backend/models",
        "backend/logs"
    ]
    
    for directory in dirs:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Created: {directory}")

def install_python_dependencies():
    """Install Python dependencies in correct order"""
    print_header("Installing Python Dependencies")
    
    # Store the original directory
    original_dir = os.getcwd()
    
    # Step 1: Upgrade pip, setuptools, and wheel
    print("\n[Step 1/5] Upgrading pip and build tools...")
    run_command(
        f"{sys.executable} -m pip install --upgrade pip setuptools wheel",
        "Upgrading pip, setuptools, and wheel"
    )
    
    # Step 2: Install Cython first (required for building madmom and other C extensions)
    print("\n[Step 2/5] Installing build dependencies...")
    run_command(
        f"{sys.executable} -m pip install 'Cython>=0.29.24'",
        "Installing Cython (required for madmom compilation)"
    )
    
    # Step 3: Install NumPy (required by many packages)
    print("\n[Step 3/5] Installing NumPy...")
    run_command(
        f"{sys.executable} -m pip install 'numpy==1.19.5'",
        "Installing NumPy (required by TensorFlow and other packages)"
    )
    
    # Step 4: Install core frameworks (PyTorch, TensorFlow)
    print("\n[Step 4/5] Installing core ML frameworks...")
    run_command(
        f"{sys.executable} -m pip install 'torch==1.13.1' 'torchaudio==0.13.1'",
        "Installing PyTorch (for Demucs)"
    )
    run_command(
        f"{sys.executable} -m pip install 'tensorflow==2.5.0'",
        "Installing TensorFlow (for Omnizart)"
    )
    
    # Step 5: Install all remaining dependencies
    print("\n[Step 5/5] Installing remaining dependencies...")
    if os.path.exists("backend/requirements.txt"):
        # Create a temporary requirements file without Cython, NumPy, PyTorch, TensorFlow
        # since we already installed them
        print("  Processing requirements.txt...")
        with open("backend/requirements.txt", "r") as f:
            lines = f.readlines()
        
        # Filter out packages we already installed
        skip_packages = ['cython', 'numpy', 'torch', 'torchaudio', 'tensorflow']
        filtered_lines = []
        for line in lines:
            line_lower = line.lower().strip()
            # Skip comments, empty lines, and already-installed packages
            if not line.strip() or line.strip().startswith('#'):
                continue
            should_skip = any(pkg in line_lower for pkg in skip_packages)
            if not should_skip:
                filtered_lines.append(line.strip())
        
        # Install remaining packages
        if filtered_lines:
            # Write to temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
                tmp.write('\n'.join(filtered_lines))
                tmp_path = tmp.name
            
            try:
                run_command(
                    f"{sys.executable} -m pip install -r {tmp_path}",
                    "Installing remaining backend dependencies"
                )
            finally:
                # Clean up temp file
                try:
                    os.remove(tmp_path)
                except:
                    pass
    
    print("\n✓ All Python dependencies installed in correct order")
    print("  1. Build tools (pip, setuptools, wheel)")
    print("  2. Cython (compilation)")
    print("  3. NumPy (base library)")
    print("  4. PyTorch & TensorFlow (ML frameworks)")
    print("  5. All other dependencies")
    
    # Return to original directory
    os.chdir(original_dir)

def download_model_checkpoints():
    """Download model checkpoints"""
    print_header("Downloading Model Checkpoints")
    
    print("Checking for AnNOTEator model...")
    annoteator_model = "AnNOTEator/inference/pretrained_models/annoteators/complete_network.h5"
    if os.path.exists(annoteator_model):
        print(f"✓ AnNOTEator model found: {annoteator_model}")
    else:
        print(f"⚠ AnNOTEator model not found at: {annoteator_model}")
        print("  Please ensure the model file is in place")
    
    print("\nChecking for Demucs models...")
    demucs_models = "AnNOTEator/inference/pretrained_models/demucs/"
    if os.path.exists(demucs_models):
        model_files = [f for f in os.listdir(demucs_models) if f.endswith('.th')]
        if model_files:
            print(f"✓ Found {len(model_files)} Demucs model(s)")
            for f in model_files:
                print(f"  - {f}")
        else:
            print(f"⚠ No Demucs .th model files found in {demucs_models}")
    else:
        print(f"⚠ Demucs models directory not found: {demucs_models}")
    
    print("\nℹ Omnizart checkpoints will be downloaded on first use if needed")

def setup_environment_file():
    """Setup .env file"""
    print_header("Setting up Environment File")
    
    if not os.path.exists("backend/.env"):
        if os.path.exists("backend/.env.example"):
            import shutil
            shutil.copy("backend/.env.example", "backend/.env")
            print("✓ Created .env file from .env.example")
            print("\n⚠ Please review and update backend/.env with your settings")
        else:
            print("⚠ No .env.example found")
    else:
        print("✓ .env file already exists")

def check_gpu():
    """Check for GPU availability"""
    print_header("Checking GPU Availability")
    
    try:
        import torch
        if torch.cuda.is_available():
            print(f"✓ CUDA is available")
            print(f"  GPU Count: {torch.cuda.device_count()}")
            for i in range(torch.cuda.device_count()):
                print(f"  GPU {i}: {torch.cuda.get_device_name(i)}")
            print("\n  You can use GPU acceleration by setting:")
            print("    DEMUCS_DEVICE=cuda")
            print("    OMNIZART_DEVICE=cuda")
        else:
            print("ℹ CUDA is not available")
            print("  The system will use CPU mode")
    except ImportError:
        print("ℹ PyTorch not installed yet")

def main():
    """Main setup function"""
    print("\n")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║          DrumScore Backend Setup Script                 ║")
    print("║          Python 3.8 Required                             ║")
    print("╚══════════════════════════════════════════════════════════╝")
    
    # Change to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Run setup steps
    check_python_version()
    check_system_dependencies()
    create_directories()
    install_python_dependencies()
    setup_environment_file()
    download_model_checkpoints()
    check_gpu()
    
    # Final message
    print_header("Setup Complete!")
    print("✓ All setup steps completed")
    print("\nNext steps:")
    print("  1. Review and update backend/.env file")
    print("  2. Run the server:")
    print("     cd backend")
    print("     python -m uvicorn main:app --host 127.0.0.1 --port 8000")
    print("  3. Visit http://127.0.0.1:8000/docs for API documentation")
    print("\nℹ️  Important:")
    print("  - Make sure you're using Python 3.8 environment (venv38)")
    print("  - On Windows, activate with: .\\venv38\\Scripts\\Activate.ps1")
    print("\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
