import requests
import time
import json

def send_notification(url: str, payload: dict):
    """
    Sends a POST request to the evaluation URL with retry logic.
    """
    headers = {"Content-Type": "application/json"}
    max_retries = 5
    # Delays will be 1, 2, 4, 8, 16 seconds
    delays = [2**i for i in range(max_retries)]

    for attempt, delay in enumerate(delays):
        try:
            print(f"Attempting to send notification to {url}...")
            print(f"Payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            
            # Raise an exception for bad status codes (4xx or 5xx)
            response.raise_for_status()

            print(f"Notification successful! Status code: {response.status_code}")
            return # Exit the function on success

        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print("All notification attempts failed.")
                raise # Re-raise the final exception to be caught in main.py