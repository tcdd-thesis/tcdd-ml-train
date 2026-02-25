import argparse
import sys
import subprocess

def main():
    # Ensure active venv
    if sys.prefix == sys.base_prefix:
        print("Please activate your virtual environment first.")
        sys.exit(1)

    # Check if roboflow is installed
    if subprocess.run([sys.executable, "-m", "pip", "show", "roboflow"]).returncode != 0:
        subprocess.run([sys.executable, "-m", "pip", "install", "roboflow"])

    # Arguments parser
    parser = argparse.ArgumentParser()
    parser.add_argument("-k", "--api-key", type=str, required=True)
    parser.add_argument("-w", "--workspace", type=str, required=True)
    parser.add_argument("-p", "--project", type=str, required=True)
    parser.add_argument("-v", "--version", type=int, required=True)
    parser.add_argument("-f", "--format", type=str, required=True)
    args = parser.parse_args()

    from roboflow import Roboflow
    rf = Roboflow(api_key=args.api_key)
    project = rf.workspace(args.workspace).project(args.project)
    version = project.version(args.version)
    dataset = version.download(args.format)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Interrupted by user (Ctrl+C). Exiting.")
        sys.exit(130)