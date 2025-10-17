import os
from dotenv import load_dotenv

print("Attempting to load .env file...")
# This loads the .env file from the current directory
load_dotenv()
print(".env file loaded.")

# Now, let's check for the keys
google_key = os.getenv("GOOGLE_API_KEY")
github_key = os.getenv("GITHUB_PAT")
secret = os.getenv("MY_SHARED_SECRET")

print(f"GOOGLE_API_KEY: {google_key}")
print(f"GITHUB_PAT: {github_key}")
print(f"MY_SHARED_SECRET: {secret}")

if google_key:
    print("\n✅ SUCCESS: Found the GOOGLE_API_KEY!")
else:
    print("\n❌ FAILURE: GOOGLE_API_KEY is not found. Check your .env file's name and location.")