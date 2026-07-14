import os
import time
from werkzeug.utils import secure_filename
from flask import current_app

try:
    import cloudinary
    import cloudinary.uploader
    from cloudinary.exceptions import Error as CloudinaryError
except ImportError:
    cloudinary = None
    CloudinaryError = Exception


def _init_cloudinary():
    """Initialize Cloudinary from current_app config or env variables."""
    if not cloudinary:
        return False
    cloud_name = current_app.config.get("CLOUDINARY_CLOUD_NAME") or os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key = current_app.config.get("CLOUDINARY_API_KEY") or os.getenv("CLOUDINARY_API_KEY")
    api_secret = current_app.config.get("CLOUDINARY_API_SECRET") or os.getenv("CLOUDINARY_API_SECRET")
    cloudinary_url = current_app.config.get("CLOUDINARY_URL") or os.getenv("CLOUDINARY_URL")

    if cloudinary_url:
        cloudinary.config(cloudinary_url=cloudinary_url)
        return True
    elif cloud_name and api_key and api_secret:
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True
        )
        return True
    return False


def upload_image(file_obj, folder="dundoo/products", prefix=""):
    """
    Upload an image file either to Cloudinary CDN (if configured) or local disk.
    Returns the URL/filename string to store in the database.
    """
    if not file_obj or not file_obj.filename:
        return None

    filename = secure_filename(file_obj.filename)
    unique_name = f"{prefix}_{int(time.time())}_{filename}" if prefix else f"{int(time.time())}_{filename}"

    if _init_cloudinary():
        try:
            current_app.logger.info(f"Uploading image to Cloudinary: {folder}/{unique_name}")
            upload_result = cloudinary.uploader.upload(
                file_obj,
                folder=folder,
                public_id=unique_name.rsplit(".", 1)[0],
                resource_type="image"
            )
            return upload_result.get("secure_url") or upload_result.get("url")
        except Exception as e:
            current_app.logger.error(f"Cloudinary image upload failed ({e}), falling back to local disk.")
            file_obj.seek(0)

    # Fallback to local storage inside frontend/static/uploads/products
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, unique_name)
    file_obj.save(file_path)
    return unique_name


def upload_video(file_obj, folder="dundoo/reels", prefix=""):
    """
    Upload a video/reel file either to Cloudinary CDN (if configured) or local disk.
    Returns the URL/filename string to store in the database (`video_url`).
    """
    if not file_obj or not file_obj.filename:
        return None

    filename = secure_filename(file_obj.filename)
    unique_name = f"{prefix}_{int(time.time())}_{filename}" if prefix else f"{int(time.time())}_{filename}"

    if _init_cloudinary():
        try:
            current_app.logger.info(f"Uploading video to Cloudinary: {folder}/{unique_name}")
            upload_result = cloudinary.uploader.upload(
                file_obj,
                folder=folder,
                public_id=unique_name.rsplit(".", 1)[0],
                resource_type="video"
            )
            return upload_result.get("secure_url") or upload_result.get("url")
        except Exception as e:
            current_app.logger.error(f"Cloudinary video upload failed ({e}), falling back to local disk.")
            file_obj.seek(0)

    # Fallback to local storage inside frontend/static/uploads/reels
    upload_dir = current_app.config["UPLOAD_REELS_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, unique_name)
    file_obj.save(file_path)
    return f"/static/uploads/reels/{unique_name}"
