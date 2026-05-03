import os
import boto3
from botocore.exceptions import ClientError
from flask import Flask, jsonify, request, render_template
from dotenv import load_dotenv
 
load_dotenv()
 
app = Flask(__name__)
 
# ---------------------------------------------------------------------------
# S3 client setup (works with Supabase S3-compatible storage)
# ---------------------------------------------------------------------------
 
def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=os.getenv("MINIO_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("MINIO_SECRET_KEY"),
        endpoint_url=os.getenv("MINIO_ENDPOINT"),
        region_name=os.getenv("MINIO_REGION", "us-east-1"),
    )
 
 
# ---------------------------------------------------------------------------
# UI route
# ---------------------------------------------------------------------------
 
@app.route("/")
def index():
    return render_template("index.html")
 
 
# ---------------------------------------------------------------------------
# Bucket operations
# ---------------------------------------------------------------------------
 
@app.route("/api/buckets", methods=["GET"])
def list_buckets():
    """List all buckets."""
    s3 = get_s3_client()
    response = s3.list_buckets()
    buckets = [b["Name"] for b in response.get("Buckets", [])]
    return jsonify({"buckets": buckets})
 
 
@app.route("/api/buckets/<bucket_name>", methods=["POST"])
def create_bucket(bucket_name):
    """Create a new bucket."""
    s3 = get_s3_client()
    try:
        s3.create_bucket(Bucket=bucket_name)
        return jsonify({"message": f"Bucket '{bucket_name}' created."})
    except ClientError as e:
        return jsonify({"error": str(e)}), 400
 
 
@app.route("/api/buckets/<bucket_name>", methods=["DELETE"])
def delete_bucket(bucket_name):
    """Delete a bucket (must be empty first)."""
    s3 = get_s3_client()
    try:
        s3.delete_bucket(Bucket=bucket_name)
        return jsonify({"message": f"Bucket '{bucket_name}' deleted."})
    except ClientError as e:
        return jsonify({"error": str(e)}), 400
 
 
# ---------------------------------------------------------------------------
# Folder operations  (S3 has no real folders — they're zero-byte key prefixes)
# ---------------------------------------------------------------------------
 
@app.route("/api/buckets/<bucket_name>/folders", methods=["POST"])
def create_folder(bucket_name):
    """Create a folder by uploading a zero-byte object ending with '/'."""
    folder_name = request.json.get("folder_name", "").strip("/") + "/"
    s3 = get_s3_client()
    try:
        s3.put_object(Bucket=bucket_name, Key=folder_name, Body=b"")
        return jsonify({"message": f"Folder '{folder_name}' created in '{bucket_name}'."})
    except ClientError as e:
        return jsonify({"error": str(e)}), 400
 
 
@app.route("/api/buckets/<bucket_name>/folders", methods=["DELETE"])
def delete_folder(bucket_name):
    """Delete a folder and all its contents."""
    folder_name = request.json.get("folder_name", "").strip("/") + "/"
    s3 = get_s3_client()
    try:
        # List and delete everything under the prefix
        paginator = s3.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket_name, Prefix=folder_name)
 
        objects_to_delete = []
        for page in pages:
            for obj in page.get("Contents", []):
                objects_to_delete.append({"Key": obj["Key"]})
 
        if objects_to_delete:
            s3.delete_objects(
                Bucket=bucket_name,
                Delete={"Objects": objects_to_delete},
            )
        return jsonify({"message": f"Folder '{folder_name}' and its contents deleted."})
    except ClientError as e:
        return jsonify({"error": str(e)}), 400
 
 
# ---------------------------------------------------------------------------
# List bucket / folder contents
# ---------------------------------------------------------------------------
 
@app.route("/api/buckets/<bucket_name>/contents", methods=["GET"])
def list_contents(bucket_name):
    """List files and sub-folders inside a bucket (or a specific prefix)."""
    prefix = request.args.get("prefix", "")
    s3 = get_s3_client()
    try:
        response = s3.list_objects_v2(
            Bucket=bucket_name,
            Prefix=prefix,
            Delimiter="/",
        )
 
        folders = [
            cp["Prefix"] for cp in response.get("CommonPrefixes", [])
        ]
        files = [
            {
                "key": obj["Key"],
                "size": obj["Size"],
                "last_modified": obj["LastModified"].isoformat(),
            }
            for obj in response.get("Contents", [])
            if not obj["Key"].endswith("/")   # skip folder markers
        ]
 
        return jsonify({"folders": folders, "files": files})
    except ClientError as e:
        return jsonify({"error": str(e)}), 400
 
 
# ---------------------------------------------------------------------------
# File operations
# ---------------------------------------------------------------------------
 
@app.route("/api/buckets/<bucket_name>/upload", methods=["POST"])
def upload_file(bucket_name):
    """Upload a file to a bucket, optionally inside a folder prefix."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided."}), 400
 
    file = request.files["file"]
    prefix = request.form.get("prefix", "").strip("/")
    key = f"{prefix}/{file.filename}" if prefix else file.filename
 
    s3 = get_s3_client()
    try:
        s3.upload_fileobj(file, bucket_name, key)
        return jsonify({"message": f"'{file.filename}' uploaded as '{key}'."})
    except ClientError as e:
        return jsonify({"error": str(e)}), 400
 
 
@app.route("/api/buckets/<bucket_name>/files", methods=["DELETE"])
def delete_file(bucket_name):
    """Delete a specific file."""
    key = request.json.get("key")
    if not key:
        return jsonify({"error": "No file key provided."}), 400
 
    s3 = get_s3_client()
    try:
        s3.delete_object(Bucket=bucket_name, Key=key)
        return jsonify({"message": f"File '{key}' deleted."})
    except ClientError as e:
        return jsonify({"error": str(e)}), 400
 
 
@app.route("/api/buckets/<bucket_name>/copy", methods=["POST"])
def copy_file(bucket_name):
    """Copy a file within S3 (same or different bucket)."""
    data = request.json
    source_key = data.get("source_key")
    dest_key = data.get("dest_key")
    dest_bucket = data.get("dest_bucket", bucket_name)
 
    if not source_key or not dest_key:
        return jsonify({"error": "source_key and dest_key are required."}), 400
 
    s3 = get_s3_client()
    try:
        s3.copy_object(
            Bucket=dest_bucket,
            CopySource={"Bucket": bucket_name, "Key": source_key},
            Key=dest_key,
        )
        return jsonify({"message": f"Copied '{source_key}' → '{dest_key}' in '{dest_bucket}'."})
    except ClientError as e:
        return jsonify({"error": str(e)}), 400
 
 
@app.route("/api/buckets/<bucket_name>/move", methods=["POST"])
def move_file(bucket_name):
    """Move = copy + delete source."""
    data = request.json
    source_key = data.get("source_key")
    dest_key = data.get("dest_key")
    dest_bucket = data.get("dest_bucket", bucket_name)
 
    if not source_key or not dest_key:
        return jsonify({"error": "source_key and dest_key are required."}), 400
 
    s3 = get_s3_client()
    try:
        # Step 1 — copy
        s3.copy_object(
            Bucket=dest_bucket,
            CopySource={"Bucket": bucket_name, "Key": source_key},
            Key=dest_key,
        )
        # Step 2 — delete original
        s3.delete_object(Bucket=bucket_name, Key=source_key)
        return jsonify({"message": f"Moved '{source_key}' → '{dest_key}' in '{dest_bucket}'."})
    except ClientError as e:
        return jsonify({"error": str(e)}), 400
 
 
# ---------------------------------------------------------------------------
 
if __name__ == "__main__":
    app.run(debug=True)