"""
Setup and launch script for Job Intelligence Dashboard.
Handles virtual environment creation, dependency installation,
database setup, job scraping, and dashboard launching.
"""
import subprocess
import sys
import os
import argparse
import platform


def get_venv_paths():
    """
    Get paths to virtual environment executables.
    Returns paths adjusted for the current operating system.
    """
    venv_dir = "venv"

    if platform.system() == "Windows":
        pip_path = os.path.join(venv_dir, "Scripts", "pip.exe")
        python_path = os.path.join(venv_dir, "Scripts", "python.exe")
        streamlit_path = os.path.join(venv_dir, "Scripts", "streamlit.exe")
    else:
        pip_path = os.path.join(venv_dir, "bin", "pip")
        python_path = os.path.join(venv_dir, "bin", "python")
        streamlit_path = os.path.join(venv_dir, "bin", "streamlit")

    return venv_dir, pip_path, python_path, streamlit_path


def setup_environment():
    """
    First-time setup: creates virtual environment, installs packages,
    and initializes the database. Safe to run multiple times.
    """
    print("Setting up Job Intelligence Dashboard...")
    print("=" * 50)

    venv_dir, pip_path, python_path, _ = get_venv_paths()

    # Create virtual environment only if it doesn't exist
    if not os.path.exists(venv_dir):
        print("Creating virtual environment...")
        subprocess.check_call([sys.executable, "-m", "venv", venv_dir])
        print("Virtual environment created")
    else:
        print("Virtual environment already exists")

    # Upgrade pip
    print("Upgrading pip...")
    try:
        subprocess.check_call([pip_path, "install", "--upgrade", "pip"])
    except subprocess.CalledProcessError:
        print("Could not upgrade pip, continuing...")

    # Install required packages one by one
    print("Installing dependencies...")
    packages = ["numpy", "pandas", "plotly", "streamlit", "requests"]

    for package in packages:
        print(f"  Installing {package}...")
        try:
            subprocess.check_call(
                [pip_path, "install", "--upgrade", package]
            )
            print(f"  {package} installed")
        except subprocess.CalledProcessError:
            print(f"  Failed to install {package}")
            # Retry without build isolation for packages that need compilation
            if package in ["pandas", "numpy"]:
                print(f"  Retrying {package}...")
                try:
                    subprocess.check_call(
                        [pip_path, "install", "--no-build-isolation", package]
                    )
                    print(f"  {package} installed with fallback")
                except subprocess.CalledProcessError:
                    print(f"  Could not install {package}")

    # Initialize database
    print("\nCreating database...")
    subprocess.check_call([python_path, "database.py"])

    print("\nSetup complete")
    print("\nCommands:")
    print("  python3 run.py --scrape    # Scrape jobs from free APIs")
    print("  python3 run.py --dashboard # Launch the dashboard")


def scrape_jobs():
    """Run the job scraper to fetch new postings."""
    _, _, python_path, _ = get_venv_paths()

    if not os.path.exists(python_path):
        print("Virtual environment not found. Run setup first:")
        print("  python3 run.py --setup")
        return

    print("Starting job scraping (using free APIs)...")
    subprocess.check_call([python_path, "scraper.py"])


def run_dashboard():
    """Launch the Streamlit dashboard."""
    _, _, _, streamlit_path = get_venv_paths()

    if not os.path.exists(streamlit_path):
        print("Streamlit not found. Run setup first:")
        print("  python3 run.py --setup")
        return

    print("Starting dashboard at http://localhost:8501 ...")
    subprocess.run(
        [streamlit_path, "run", "app.py", "--server.port", "8501"]
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Job Intelligence Dashboard"
    )
    parser.add_argument(
        '--setup', action='store_true',
        help='First-time setup (venv, packages, database)'
    )
    parser.add_argument(
        '--scrape', action='store_true',
        help='Scrape new job postings'
    )
    parser.add_argument(
        '--dashboard', action='store_true',
        help='Launch the Streamlit dashboard'
    )

    args = parser.parse_args()

    if args.setup:
        setup_environment()
    elif args.scrape:
        scrape_jobs()
    elif args.dashboard:
        run_dashboard()
    else:
        # Show available commands if none specified
        _, _, python_path, _ = get_venv_paths()
        if not os.path.exists(python_path):
            print("First time? Run: python3 run.py --setup")
        else:
            print("Available commands:")
            print("  python3 run.py --setup     # Reinstall packages")
            print("  python3 run.py --scrape    # Scrape new jobs")
            print("  python3 run.py --dashboard # Open dashboard")