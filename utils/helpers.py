"""Helper utility functions"""
import sys
import subprocess
import threading
import requests
import argostranslate.translate
import argostranslate.package
import logging

log = logging.getLogger("Translator")

def ensure_dependencies():
    """Check and install missing dependencies"""
    from config.constants import REQUIRED_PACKAGES
    
    missing = []
    for pkg in REQUIRED_PACKAGES:
        try:
            __import__(pkg.replace('-', '_').split('[')[0])
        except ImportError:
            missing.append(pkg)
    
    if missing:
        print(f"\n{'='*60}\nMissing Dependencies\n{'='*60}")
        print("The following packages need to be installed:")
        for pkg in missing:
            print(f"  • {pkg}")
        print(f"\nTotal size: ~500MB (includes PyTorch and Whisper)\n{'='*60}")
        
        # Auto-install in non-interactive mode
        print("Auto-installing missing packages...")
        for pkg in missing:
            print(f"\n📦 Installing {pkg}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg])
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install {pkg}: {e}")
                continue
        print("\n✅ Dependencies installation completed!\n")

def is_online():
    """Check if internet connection is available"""
    try:
        requests.get("https://www.google.com", timeout=3)
        return True
    except:
        return False

def setup_argos():
    """Setup Argos offline translation packages"""
    try:
        argostranslate.package.update_package_index()
        available = argostranslate.package.get_available_packages()
        installed = {l.code for l in argostranslate.translate.get_installed_languages()}
        for from_l in ["en", "fr", "es"]:
            for to_l in ["en", "fr", "es"]:
                if from_l != to_l and from_l not in installed:
                    pkg = next((p for p in available if p.from_code==from_l and p.to_code==to_l), None)
                    if pkg:
                        argostranslate.package.install_from_path(pkg.download())
    except Exception as e:
        log.warning(f"Argos setup failed: {e}")

# Start Argos setup in background thread
threading.Thread(target=setup_argos, daemon=True).start()
