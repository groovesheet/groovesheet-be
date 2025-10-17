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
    """Install Python dependencies"""
    print_header("Installing Python Dependencies")
    
    # Upgrade pip
    run_command(
        f"{sys.executable} -m pip install --upgrade pip",
        "Upgrading pip"
    )
    
    # Install backend requirements
    if os.path.exists("backend/requirements.txt"):
        run_command(
            f"{sys.executable} -m pip install -r backend/requirements.txt",
            "Installing backend requirements"
        )
    
    # Install Demucs
    if os.path.exists("demucs"):
        os.chdir("demucs")
        run_command(
            f"{sys.executable} -m pip install -e .",
            "Installing Demucs"
        )
        os.chdir("..")
    
    # Install Omnizart
    if os.path.exists("omnizart"):
        os.chdir("omnizart")
        run_command(
            f"{sys.executable} -m pip install -e .",
            "Installing Omnizart"
        )
        os.chdir("..")

def download_model_checkpoints():
    """Download model checkpoints"""
    print_header("Downloading Model Checkpoints")
    
    print("This may take several minutes...")
    try:
        import omnizart
        from omnizart.cli.cli import download_checkpoints
        download_checkpoints()
        print("✓ Omnizart checkpoints downloaded")
    except Exception as e:
        print(f"⚠ Could not download checkpoints: {e}")
        print("  Checkpoints will be downloaded on first use")

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
    print("     python main.py")
    print("  3. Visit http://localhost:8000/docs for API documentation")
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
