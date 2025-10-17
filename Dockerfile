# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /code

# Copy the requirements file and install dependencies
# Note: Copying pyproject.toml isn't necessary if you only use requirements.txt
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy the rest of the application code
COPY . /code/

# NEW: Expose the port Hugging Face expects
EXPOSE 7860

# MODIFIED: Run Uvicorn on the correct host and port
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]