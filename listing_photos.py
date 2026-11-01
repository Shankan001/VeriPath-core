import io
import secrets
from PIL import Image, ImageOps
from supabase_db import get_client, SUPABASE_URL

BUCKET = "listing-photos"
MAX_PHOTOS_PER_LISTING = 4
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
MAX_SIDE_PX = 1600


def clean_image(raw: bytes) -> bytes:
    """Return a brand-new JPEG with ZERO metadata (no EXIF, no GPS, no XMP,
    no ICC). Raises ValueError if the input is not a decodable image."""
    if not raw:
        raise ValueError("Empty file.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("File too large (max 15 MB).")
    try:
        im = Image.open(io.BytesIO(raw))
        im.load()
    except Exception:
        raise ValueError("That file is not a readable image.")
    # Apply the phone's rotation BEFORE metadata is discarded.
    im = ImageOps.exif_transpose(im)
    im = im.convert("RGB")
    im.thumbnail((MAX_SIDE_PX, MAX_SIDE_PX))
    # Copy pixels into a fresh image so nothing from the original
    # (info dict, exif, icc profile) can be carried over.
    fresh = Image.new("RGB", im.size)
    fresh.paste(im)
    out = io.BytesIO()
    fresh.save(out, "JPEG", quality=85, optimize=True)
    return out.getvalue()


def new_photo_path() -> str:
    # Random name only: no tag, company, farm or user in the path.
    return f"{secrets.token_hex(8)}.jpg"


def upload_listing_photo(raw: bytes) -> str:
    """Clean, then upload to the PUBLIC listing-photos bucket.
    Returns the storage path. Raises on any failure."""
    data = clean_image(raw)
    path = new_photo_path()
    get_client().storage.from_(BUCKET).upload(
        path, data, {"content-type": "image/jpeg"})
    return path


def delete_listing_photo(path: str) -> None:
    get_client().storage.from_(BUCKET).remove([path])


def public_url(path: str) -> str:
    return f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/public/{BUCKET}/{path}"
