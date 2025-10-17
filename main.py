# In main.py
# This is a test comment to create a new commit.
import os
import json
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

# Import your modules
import llm_generator
import github_manager
import notifier
import state_manager 
import attachment_manager

app = FastAPI()

def process_build_request(data: dict):
    """The core logic for the entire build and deploy process."""
    task_id = data.get("task")
    round_number = data.get("round", 1)
    print("--------------------------------------------------")
    print(f"BACKGROUND: Starting processing for task: {task_id}, round: {round_number}")
    saved_attachments_meta = [] # Keep track of saved files for cleanup

    try:
        if round_number > 1:
            print("PHASE 0: Retrieving state for revision...")
            task_state = state_manager.get_task_state(task_id)
            if not task_state or "repo_name" not in task_state:
                print(f"ERROR: No previous state found for task {task_id}. Cannot perform revision.")
                return 

            repo_name = task_state["repo_name"]
            print(f"PHASE 0: Fetching existing code from '{repo_name}'...")
            existing_code = github_manager.get_repo_contents(repo_name)
            if not existing_code:
                print(f"Warning: Could not fetch code from repo '{repo_name}'.")
            
                print(f"ERROR: Could not fetch code from repo '{repo_name}'. Cannot perform revision.")
                return

            data["existing_code"] = existing_code
            data["repo_name"] = repo_name 

        # --- NEW: Handle attachments first ---
        print("PHASE 0.5: Processing attachments...")
        attachments = data.get("attachments", [])
        saved_attachments_meta = attachment_manager.save_attachments_to_disk(attachments)
        print(f"PHASE 0.5: Saved {len(saved_attachments_meta)} attachments to disk.")

        print("PHASE 1: Generating code with LLM...")
        generated_files = llm_generator.generate_app_code(data, saved_attachments_meta)
        if "error.txt" in generated_files:
            print("ERROR: LLM generation failed. Stopping process.")
            return
        
        print(f"PHASE 1: Code generation complete. Files: {list(generated_files.keys())}")

        print("PHASE 2: Managing GitHub repository...")
        repo_details = github_manager.create_or_update_repo(
            request_data=data, 
            generated_files=generated_files, 
            attachment_meta=saved_attachments_meta
        )
        print(f"PHASE 2: GitHub management complete. URL: {repo_details.get('repo_url')}")
        
        if round_number == 1:
            state_manager.save_task_state(task_id, {
                "repo_name": repo_details.get("repo_name"),
                "repo_url": repo_details.get("repo_url")
            })

        print("PHASE 3: Notifying evaluation server...")
        notification_payload = {
            "email": data.get("email"),
            "task": data.get("task"),
            "round": data.get("round"),
            "nonce": data.get("nonce"),
            "repo_url": repo_details.get("repo_url"),
            "commit_sha": repo_details.get("commit_sha"),
            "pages_url": repo_details.get("pages_url"),
        }
        evaluation_url = data.get("evaluation_url")
        notifier.send_notification(evaluation_url, notification_payload)
        print("PHASE 3: Notification sent successfully.")

        print(f"BACKGROUND: Successfully processed task: {task_id}")
        print("--------------------------------------------------")

    except Exception as e:
        print(f"BACKGROUND: An error occurred during processing task {task_id}: {e}")
    finally:
        # --- NEW: Always clean up temporary files ---
        attachment_manager.cleanup_attachments(saved_attachments_meta)

@app.post("/api/build")
async def handle_build_request(request: Request, background_tasks: BackgroundTasks):
    try:
        data = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    expected_secret = os.getenv("MY_SHARED_SECRET")
    if not expected_secret or data.get("secret") != expected_secret:
        raise HTTPException(status_code=403, detail="Invalid secret provided")

    print(f"SUCCESS: Valid secret received for task: {data.get('task')}, round: {data.get('round')}")
    background_tasks.add_task(process_build_request, data)
    return {"status": "Request received. Processing in background."}

@app.get("/")
def read_root():
    return {"status": "API is running"}
