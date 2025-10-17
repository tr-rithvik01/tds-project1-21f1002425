import json
import os
from typing import Optional, Dict

STATE_FILE = "/tmp/repo_state.json"

def save_task_state(task_id: str, details: Dict):
    """Saves the repository details for a given task ID."""
    state = load_all_states()
    state[task_id] = details
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        print(f"Saved state for task: {task_id}")
    except IOError as e:
        print(f"Error saving state to {STATE_FILE}: {e}")

def get_task_state(task_id: str) -> Optional[Dict]:
    """Loads the repository details for a specific task ID."""
    state = load_all_states()
    return state.get(task_id)

def load_all_states() -> Dict:
    """Loads the entire state file from disk."""
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, 'r') as f:
            content = f.read()
            if not content:
                return {}
            return json.loads(content)
    except (json.JSONDecodeError, IOError):
        return {}

