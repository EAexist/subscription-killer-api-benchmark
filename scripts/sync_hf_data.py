import os
import shutil
from huggingface_hub import snapshot_download
from dotenv import load_dotenv

load_dotenv()

def sync_data():
    repo_id = os.getenv("HF_REPO_ID")
    local_dir = os.getenv("HF_LOCAL_DIR")
    
    if not repo_id or not local_dir:
        raise ValueError("HF_REPO_ID and HF_LOCAL_DIR are required")

    # --- CLEANING STEP ---
    if os.path.exists(local_dir):
        print(f"Cleaning existing data in {local_dir}...")
        # Option A: Delete everything
        shutil.rmtree(local_dir) 

    print(f"Downloading fresh snapshot from {repo_id}...")
    snapshot_download(
        repo_id=repo_id,
        repo_type="dataset",
        local_dir=local_dir,
        ignore_patterns=["*.md", ".gitattributes"]
    )
    
    # --- RESTORE ESSENTIALS ---
    # Ensure __init__.py exists so the parent project can import it
    init_path = os.path.join(local_dir, "src", "__init__.py")
    if not os.path.exists(init_path):
        os.makedirs(os.path.dirname(init_path), exist_ok=True)
        open(init_path, 'a').close()

    print("Data is perfectly mirrored.")

if __name__ == "__main__":
    sync_data()