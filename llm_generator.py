import os
import json
import google.generativeai as genai

# Your existing Gemini initialization code...
try:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables.")
    genai.configure(api_key=api_key)
    # Using a modern, capable model
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    print(f"Error initializing Gemini client: {e}")
    model = None

def _create_attachment_summary_for_prompt(saved_files_meta: list) -> str:
    """Creates a text summary of attachments for the LLM prompt."""
    if not saved_files_meta:
        return "No attachments provided.\n"

    summary = ""
    for meta in saved_files_meta:
        name = meta['name']
        path = meta['path']
        is_text_based = any(name.lower().endswith(ext) for ext in ['.txt', '.csv', '.json', '.md', '.html', '.css', '.js'])

        if is_text_based:
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    preview = f.read(500)
                summary += f"- Filename: '{name}'. Content preview: '{preview}...'\n"
            except Exception as e:
                summary += f"- Filename: '{name}'. (Could not read preview: {e})\n"
        else:
            summary += f"- Filename: '{name}'. (This is a binary image file. You MUST reference it in your HTML using an <img> tag, for example: <img src=\"{name}\" alt=\"Logo\">)\n"
    return summary

def generate_app_code(request_data: dict, saved_attachments_meta: list) -> dict:
    if not model:
        raise ConnectionError("Gemini client is not initialized.")

    brief = request_data.get("brief", "")
    checks = request_data.get("checks", [])
    round_number = request_data.get("round", 1)

    # This prompt is the 'System Prompt' and sets the rules for the AI
    full_prompt = """
You are an expert full-stack web developer. Your task is to generate or modify the complete code for a web app based on a given brief.
You MUST return your response as a single, valid JSON object. The JSON object must have filenames as keys and the file content as string values.
Do not include any explanations or markdown formatting outside of the JSON object itself.

# --- START: NEW INSTRUCTION ---
**VERY IMPORTANT: All string values in the JSON MUST be properly escaped according to standard JSON format.**
- **Newlines** must be escaped as `\\n`.
- **Double quotes** must be escaped as `\\"`.
- **Backslashes** must be escaped as `\\\\`.
# --- END: NEW INSTRUCTION ---

Do not include any explanations or markdown formatting outside of the JSON object itself.
...
**CRITICAL: Your response MUST include a comprehensive README.md file with the following sections:**
1.  **Project Title and Description:** A summary of the application's purpose.
2.  **Setup Instructions:** How to run the app locally (if applicable).
3.  **Usage Guide:** How to use the application.
4.  **Code Explanation:** A brief overview of the file structure and logic.
5.  **License Information:** State that it is under the MIT License.

The README.md must be professional and complete.
---
"""
    # This is the 'User Prompt' with the specific task
    user_prompt = f"""
Please generate or modify the code for a web application based on the following requirements.

**Project Brief:**
{brief}

**Evaluation Checks (Your code must satisfy these):**
- {"\n- ".join(checks)}

**Attachments:**
{_create_attachment_summary_for_prompt(saved_attachments_meta)}
"""

    # Add revision-specific instructions
    if round_number > 1:
        existing_code = request_data.get("existing_code")
        if existing_code and isinstance(existing_code, dict):
            code_to_show = {k: v for k, v in existing_code.items() if not k.startswith('.github')}
            # --- START: NEW, IMPROVED CODE ---
            user_prompt += "\n"
            user_prompt += "**This is a revision request. Please modify the following existing code based on the new brief.**\n"
            user_prompt += "**Crucially, you MUST also update the README.md to describe the new features and changes.**\n"
            user_prompt += "**Your response must include ALL necessary files for the project, including any unchanged files.**\n\n"
            user_prompt += "### EXISTING CODE TO REVISE ###\n"

            # Instead of json.dumps, loop through the files and present them cleanly.
            for filename, content in code_to_show.items():
                user_prompt += f"--- START FILE: {filename} ---\n"
                user_prompt += f"{content}\n"
                user_prompt += f"--- END FILE: {filename} ---\n\n"
            # --- END: NEW, IMPROVED CODE ---
            user_prompt += "\n"
    
    full_prompt += user_prompt

    print("--- Sending Prompt to Gemini ---")
    print(full_prompt)
    print("--------------------------------")

    try:
        generation_config = genai.types.GenerationConfig(
            response_mime_type="application/json"
        )
        
        # --- START: MODIFIED CODE ---
        completion = model.generate_content(
            full_prompt,
            generation_config=generation_config
        )

        response_content = completion.text

        # --- NEW: More robust JSON cleaning and parsing ---
        # Find the start of the JSON object '{'
        json_start_index = response_content.find('{')
        if json_start_index != -1:
            json_str = response_content[json_start_index:]
            # Use raw_decode which can handle trailing characters or truncated responses
            try:
                decoder = json.JSONDecoder()
                generated_files, _ = decoder.raw_decode(json_str)
            except json.JSONDecodeError as e:
                print(f"ERROR: Failed to decode JSON. Error: {e}")
                print(f"--- Problematic String ---:\n{json_str}\n--------------------")
                raise ValueError("LLM response could not be parsed as JSON.") from e
        else:
            # If no JSON object is found at all, raise an error
            print(f"--- Invalid Response ---:\n{response_content}\n--------------------")
            raise ValueError("LLM response did not contain a valid JSON object.")
        # --- END: MODIFIED CODE ---
        
        if not isinstance(generated_files, dict) or "index.html" not in generated_files or "README.md" not in generated_files:
             raise ValueError("LLM response is invalid. It must be a JSON object containing at least 'index.html' and 'README.md'.")

        return generated_files

    except Exception as e:
        print(f"ERROR: An unexpected error occurred with the Gemini API: {e}")
        return {"error.txt": f"An API error occurred: {e}"}
