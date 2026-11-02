import io, sys, requests
from PIL import Image
import listing_photos as lp


def exif_report(raw: bytes):
    im = Image.open(io.BytesIO(raw))
    ex = im.getexif()
    gps = dict(ex.get_ifd(0x8825))
    return len(ex), gps, sorted(im.info.keys())


def make_gps_jpeg() -> bytes:
    im = Image.new("RGB", (2400, 1600), (120, 90, 60))
    ex = Image.Exif()
    ex[0x010F] = "TestPhone"            # Make
    gps = ex.get_ifd(0x8825)
    gps[1] = "S"; gps[2] = (1.0, 17.0, 30.0)     # fake latitude
    gps[3] = "E"; gps[4] = (36.0, 49.0, 15.0)    # fake longitude
    buf = io.BytesIO()
    im.save(buf, "JPEG", exif=ex)
    return buf.getvalue()


# Optional: pass a real photo path to test it too.
raw = open(sys.argv[1], "rb").read() if len(sys.argv) > 1 else make_gps_jpeg()

n, gps, _ = exif_report(raw)
print(f"INPUT : exif tags={n}, GPS={'YES' if gps else 'NONE'}")
if len(sys.argv) == 1:
    assert gps, "test image should contain GPS before cleaning"

cleaned = lp.clean_image(raw)
n2, gps2, info2 = exif_report(cleaned)
print(f"CLEAN : exif tags={n2}, GPS={'YES' if gps2 else 'NONE'}, info keys={info2}")
assert n2 == 0, "EXIF tags survived cleaning"
assert not gps2, "GPS survived cleaning"
assert "exif" not in info2 and "icc_profile" not in info2 and "xmp" not in info2
w, h = Image.open(io.BytesIO(cleaned)).size
assert max(w, h) <= lp.MAX_SIDE_PX, "not resized"

path = lp.upload_listing_photo(raw)
try:
    url = lp.public_url(path)
    r = requests.get(url, timeout=30)
    assert r.status_code == 200, f"public download failed: HTTP {r.status_code}"
    n3, gps3, _ = exif_report(r.content)
    print(f"STORED: {url}\n        exif tags={n3}, GPS={'YES' if gps3 else 'NONE'}")
    assert n3 == 0 and not gps3, "stored file still has metadata"
    assert len(path) == 20 and path.endswith(".jpg"), "unexpected filename shape"
finally:
    lp.delete_listing_photo(path)
    print("test file deleted")

print("\nPASS: GPS and all EXIF removed, resized, public URL works.")
