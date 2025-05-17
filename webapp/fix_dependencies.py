import subprocess
import sys
import pkg_resources

def check_and_fix_dependencies():
    print("Checking Flask and Werkzeug versions...")
    
    try:
        flask_version = pkg_resources.get_distribution("flask").version
        werkzeug_version = pkg_resources.get_distribution("werkzeug").version
        print(f"Found Flask {flask_version} and Werkzeug {werkzeug_version}")
        
        # Check if we need to downgrade Flask or fix Werkzeug
        if werkzeug_version.startswith('2.1') or werkzeug_version.startswith('2.2'):
            print("Detected incompatible Werkzeug version. Fixing dependencies...")
            
            # Install compatible versions
            subprocess.check_call([sys.executable, "-m", "pip", "install", "flask==2.0.1", "werkzeug==2.0.2"])
            print("✅ Successfully installed compatible versions: Flask 2.0.1 and Werkzeug 2.0.2")
        
        # For Python 3.12, we need newer Flask version
        if sys.version_info >= (3, 12):
            print("Python 3.12 detected. Installing latest compatible Flask...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "flask>=2.2.5", "werkzeug>=2.2.3"])
            print("✅ Successfully installed Flask and Werkzeug versions compatible with Python 3.12")
            
    except pkg_resources.DistributionNotFound:
        print("Flask or Werkzeug not found. Installing compatible versions...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "flask==2.0.1", "werkzeug==2.0.2"])
        print("✅ Successfully installed Flask 2.0.1 and Werkzeug 2.0.2")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Please run the following commands manually:")
        print("pip uninstall -y flask werkzeug")
        print("pip install flask==2.0.1 werkzeug==2.0.2")
    
    print("\nNow try running your Flask application again.")

if __name__ == "__main__":
    check_and_fix_dependencies()
