import os
import time
from io import BytesIO
from werkzeug.utils import secure_filename
from flask import current_app

try:
    import cloudinary
    import cloudinary.uploader
    from cloudinary.exceptions import Error as CloudinaryError
except ImportError:
    cloudinary = None
    CloudinaryError = Exception

try:
    from PIL import Image
except ImportError:
    Image = None


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


def _compress_image(file_obj, max_dimension=1080, quality=75):
    """
    Compress and downscale image in memory before uploading or saving.
    Drastically reduces image size (often by 85-95% down to ~50-80KB) to keep
    Cloudinary data storage and bandwidth usage extremely low.
    """
    if not Image:
        return file_obj, False

    try:
        file_obj.seek(0)
        img = Image.open(file_obj)

        # Handle transparent RGBA / P mode images by pasting onto white background
        if img.mode in ("RGBA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "RGBA":
                background.paste(img, mask=img.split()[3])
            else:
                background.paste(img)
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Resize image if either dimension exceeds max_dimension while maintaining aspect ratio
        width, height = img.size
        if width > max_dimension or height > max_dimension:
            img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

        # Save compressed JPEG into an in-memory BytesIO buffer
        compressed_buffer = BytesIO()
        img.save(compressed_buffer, format="JPEG", quality=quality, optimize=True)
        compressed_buffer.seek(0)
        return compressed_buffer, True
    except Exception as e:
        if current_app:
            current_app.logger.warning(f"Image compression skipped due to error ({e}), using original file.")
        file_obj.seek(0)
        return file_obj, False


def upload_image(file_obj, folder="dundoo/products", prefix=""):
    """
    Upload a compressed image file either to Cloudinary CDN (if configured) or local disk.
    Returns the URL/filename string to store in the database.
    """
    if not file_obj or not file_obj.filename:
        return None

    filename = secure_filename(file_obj.filename)
    unique_name = f"{prefix}_{int(time.time())}_{filename}" if prefix else f"{int(time.time())}_{filename}"

    # 1. Pre-compress in Python memory to reduce file size to ~50KB-80KB before storage
    compressed_file, was_compressed = _compress_image(file_obj, max_dimension=1080, quality=75)
    if was_compressed and not unique_name.lower().endswith((".jpg", ".jpeg")):
        unique_name = unique_name.rsplit(".", 1)[0] + ".jpg"

    # 2. Upload compressed image to Cloudinary with CDN auto-optimization flags
    if _init_cloudinary():
        try:
            current_app.logger.info(f"Uploading compressed image to Cloudinary: {folder}/{unique_name}")
            upload_result = cloudinary.uploader.upload(
                compressed_file,
                folder=folder,
                public_id=unique_name.rsplit(".", 1)[0],
                resource_type="image",
                # Cloudinary transformation to guarantee lowest possible delivery storage & bandwidth (WebP/AVIF auto-format)
                transformation=[
                    {"width": 1080, "height": 1080, "crop": "limit"},
                    {"quality": "auto:low", "fetch_format": "auto"}
                ]
            )
            return upload_result.get("secure_url") or upload_result.get("url")
        except Exception as e:
            current_app.logger.error(f"Cloudinary image upload failed ({e}), falling back to local disk.")
            compressed_file.seek(0)

    # 3. Fallback to local disk storage (`frontend/static/uploads/products`)
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, unique_name)
    
    if hasattr(compressed_file, "save") and not isinstance(compressed_file, BytesIO):
        compressed_file.save(file_path)
    else:
        with open(file_path, "wb") as f:
            f.write(compressed_file.read())
            
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
                resource_type="video",
                # Optimize video storage & bitrate on Cloudinary
                eager=[
                    {"width": 720, "height": 1280, "crop": "limit", "quality": "auto", "video_codec": "auto"}
                ]
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
