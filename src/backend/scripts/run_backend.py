"""
Run VM.AI Backend Server
"""
import subprocess
import sys
import os

def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    print("Starting VM.AI Backend...")
    print("Server will be available at: http://127.0.0.1:8000")
    print("Press Ctrl+C to stop the server\n")
    
    subprocess.run([
        "uv", "run", "uvicorn", "app.main:app",
        "--reload", "--host", "127.0.0.1", "--port", "8000"
    ])

if __name__ == "__main__":
    main()