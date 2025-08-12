#!/usr/bin/env python3
"""
Setup script for the Telegram Notes Bot.
Helps users install dependencies and set up the environment.
"""
import os
import sys
import subprocess
import shutil


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required.")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True


def install_dependencies():
    """Install required Python packages."""
    print("📦 Installing Python dependencies...")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False


def setup_env_file():
    """Set up the .env file if it doesn't exist."""
    if os.path.exists(".env"):
        print("✅ .env file already exists")
        return True
    
    print("📝 Setting up .env file...")
    
    try:
        shutil.copy(".env.example", ".env")
        print("✅ .env file created from template")
        print("⚠️  Please edit .env and add your BOT_TOKEN")
        return True
    except FileNotFoundError:
        print("❌ .env.example not found")
        return False


def check_ollama():
    """Check if Ollama is available."""
    print("🔍 Checking for Ollama...")
    
    try:
        result = subprocess.run(["ollama", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Ollama found: {result.stdout.strip()}")
            return True
        else:
            print("❌ Ollama not found or not working")
            return False
    except FileNotFoundError:
        print("❌ Ollama not installed")
        return False


def main():
    """Main setup function."""
    print("🚀 Setting up Telegram Notes Bot...\n")
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Setup environment file
    if not setup_env_file():
        sys.exit(1)
    
    # Check Ollama (optional)
    ollama_available = check_ollama()
    
    print("\n🎉 Setup completed!")
    print("\n📋 Next steps:")
    print("1. Edit .env file and add your BOT_TOKEN")
    
    if not ollama_available:
        print("2. Install and start Ollama (optional):")
        print("   curl -fsSL https://ollama.ai/install.sh | sh")
        print("   ollama pull llama2")
        print("   ollama serve")
    else:
        print("2. Start Ollama service:")
        print("   ollama serve")
    
    print("3. Run the bot:")
    print("   python bot.py")
    
    print("\n📚 For more information, see README.md")


if __name__ == "__main__":
    main()