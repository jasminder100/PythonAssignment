# S3 File Manager
S3 File Manager is a browser-based tool that lets you manage files and folders stored in MinIO (an S3-compatible object storage system) without writing a single line of code or using the command line. 

# Stack

Backend — Python 3, Flask, Boto3
Storage — MinIO (S3-compatible)
Frontend — HTML, CSS, JavaScript

# Setup
1. Install dependencies
  - python3 -m venv venv
  - source venv/bin/activate
  - pip install -r requirements.txt
2. Configure environment
  - cp env.example .env
3. Start MinIO
  - minio server ~/minio-data --console-address ":9001"
4. Run the app
  - python3 app.py

# Features

1) Organise storage by creating and deleting buckets — think of buckets as top-level drives or containers for your files.
2) Create folders inside buckets to keep your files structured, just like folders on your computer.
3) Upload any file — documents, images, videos — directly from your browser into any bucket or folder.
4) Delete files or entire folders when you no longer need them.
5) Copy a file to duplicate it in the same or a different bucket without re-uploading.
6) Move a file to relocate it from one place to another cleanly.
7) Browse contents of any bucket to see exactly what files and folders are inside.

# Use Case

This tool is useful for anyone who needs a simple, visual way to manage local or cloud S3-compatible storage — whether you are a developer testing file uploads, a student learning about object storage, or someone who just wants a cleaner alternative to the MinIO web console.

