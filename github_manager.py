import os
import time
import requests
from github import Github, GithubException
import base64

def create_or_update_repo(request_data: dict, generated_files: dict, attachment_meta: list) -> dict:
    """Creates or updates a GitHub repository, enables Pages, and populates it with files."""
    github_pat = os.getenv("GITHUB_PAT")
    g = Github(github_pat)
    user = g.get_user()
    
    task_id = request_data.get("task")
    round_number = request_data.get("round", 1)
    
    repo_name = request_data.get("repo_name") 
    if not repo_name: 
        nonce = request_data.get("nonce")
        repo_name = f"llm-app-{task_id}-{nonce}"

    # Create a lookup map from filename to its temporary disk path
    attachment_paths = {meta['name']: meta['path'] for meta in attachment_meta}

    repo = None
    commit_sha = None

    try:
        if round_number == 1:
            try:
                existing_repo = user.get_repo(repo_name)
                print(f"Repo '{repo_name}' already exists. Deleting for a fresh start.")
                existing_repo.delete()
                time.sleep(2)
            except GithubException as e:
                if e.status != 404: raise
            
            print(f"Creating new public repository '{repo_name}' with MIT license...")
            # Use auto_init and license_template to create the repo with a license from the start.
            repo = user.create_repo(repo_name, private=False, auto_init=True, license_template="mit")
            time.sleep(2)
        else:
            print(f"Fetching existing repository: '{repo_name}' for update.")
            repo = user.get_repo(repo_name)

        print("Preparing to commit files...")

        for filename, content in generated_files.items():
            commit_content = content

            # If this file was an original attachment, read its content from disk.
            if filename in attachment_paths:
                try:
                    with open(attachment_paths[filename], "rb") as f:
                        commit_content = f.read()
                except Exception as e:
                    print(f"ERROR: Could not read attachment file from disk: {attachment_paths[filename]}. Skipping. Error: {e}")
                    continue # Skip this file
            
            commit_message = f"feat: Add/update {filename} for round {round_number}"
            commit_sha = commit_file(repo, filename, commit_content, commit_message)
            print(f"  - Committed '{filename}'")

        if round_number == 1:
            # The LICENSE is now created automatically, so we only need to add the workflow.
            workflow_content = get_deploy_workflow_content()
            commit_sha = commit_file(repo, ".github/workflows/deploy.yml", workflow_content, "ci: Add GitHub Pages deployment workflow")
            print("  - Committed deployment workflow")
        
        # --- NEW: Enable GitHub Pages via API ---
        if round_number == 1:
            print("Enabling GitHub Pages programmatically...")
            enable_github_pages(github_pat, repo.full_name)
            
        repo_url = repo.html_url
        pages_url = f"https://{user.login}.github.io/{repo.name}/"
        
        print(f"Successfully configured repo. URL: {repo_url}")
        
        return {
            "repo_name": repo.name,
            "repo_url": repo_url,
            "pages_url": pages_url,
            "commit_sha": commit_sha
        }

    except Exception as e:
        print(f"ERROR: An unexpected error occurred in github_manager: {e}")
        raise

def enable_github_pages(github_pat: str, repo_full_name: str):
    """Enables GitHub Pages for the main branch using the REST API."""
    headers = {
        "Authorization": f"token {github_pat}",
        "Accept": "application/vnd.github.v3+json",
    }
    url = f"https://api.github.com/repos/{repo_full_name}/pages"
    data = {
        "source": {"branch": "main", "path": "/"}
    }
    
    # Give GitHub a moment for the main branch to be fully ready
    time.sleep(5) 
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        print("GitHub Pages enabled successfully.")
    else:
        print(f"Warning: Could not enable GitHub Pages via API. Status: {response.status_code}, Response: {response.text}")
        print("The GitHub Actions workflow will act as a backup.")

def commit_file(repo, path: str, content: str or bytes, message: str) -> str:
    """Commits a file to the repository, creating or updating it."""
    try:
        existing_file = repo.get_contents(path, ref="main")
        result = repo.update_file(path, message, content, existing_file.sha, branch="main")
        return result['commit'].sha
    except GithubException as e:
        if e.status == 404: # File does not exist, create it
            result = repo.create_file(path, message, content, branch="main")
            return result['commit'].sha
        else:
            raise

def get_repo_contents(repo_name: str) -> dict:
    github_pat = os.getenv("GITHUB_PAT")
    g = Github(github_pat)
    user = g.get_user()
    repo = user.get_repo(repo_name)
    tree = repo.get_git_tree("main", recursive=True).tree
    file_contents = {}
    for element in tree:
        if element.type == 'blob':
            try:
                content = repo.get_contents(element.path).decoded_content.decode('utf-8')
                file_contents[element.path] = content
            except (UnicodeDecodeError, GithubException):
                pass 
    return file_contents

def get_deploy_workflow_content() -> str:
    """Returns the GitHub Actions workflow file content as a string."""
    return """
name: Deploy static content to Pages
on:
  push:
    branches: ["main"]
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: "pages"
  cancel-in-progress: false
jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Setup Pages
        uses: actions/configure-pages@v4
      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: '.'
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
"""
