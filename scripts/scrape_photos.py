"""
Scrapes and re-hosts fighter photos to Supabase Storage.
Processes all fighters missing photos, 50 at a time.
Run manually to bulk-fill, then the weekly pipeline handles new fighters.
"""
import os, time, logging, requests
from bs4 import BeautifulSoup
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger("photos")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.ufc.com/",
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
}

def get_photo_url(first_name, last_name, ufc_id=None):
    slug = ufc_id or (
        f"{first_name}-{last_name}"
        .lower().replace(" ", "-").replace("'", "").replace(".", "").replace(" ", "-")
    )
    try:
        page = requests.get(
            f"https://www.ufc.com/athlete/{slug}",
            headers={"User-Agent": HEADERS["User-Agent"]},
            timeout=12
        )
        if page.status_code != 200:
            return None, slug
        soup = BeautifulSoup(page.text, "html.parser")
        img = (
            soup.select_one("img.hero-profile__image") or
            soup.select_one(".c-bio__image img") or
            soup.select_one(".hero-profile img") or
            soup.select_one('img[src*="/styles/athlete_bio_full_body"]') or
            soup.select_one('img[src*="athlete"]')
        )
        if not img: return None, slug
        src = img.get("src") or img.get("data-src", "")
        if not src or "placeholder" in src.lower(): return None, slug
        if src.startswith("//"): src = "https:" + src
        elif src.startswith("/"): src = "https://www.ufc.com" + src
        return src, slug
    except Exception as e:
        log.debug(f"Page fetch failed for {slug}: {e}")
        return None, slug

def download_and_store(fighter_id, photo_url, slug):
    try:
        r = requests.get(photo_url, headers=HEADERS, timeout=15)
        if r.status_code != 200: return None
        ct = r.headers.get("content-type", "image/jpeg")
        ext = "jpg" if "jpeg" in ct else ct.split("/")[-1].split(";")[0]
        path = f"{fighter_id}.{ext}"
        db.storage.from_("fighter-photos").upload(
            path, r.content,
            file_options={"content-type": ct, "upsert": "true"}
        )
        return db.storage.from_("fighter-photos").get_public_url(path)
    except Exception as e:
        log.debug(f"Upload failed for {slug}: {e}")
        return None

def main():
    # Check total missing
    all_missing = db.table("fighters").select(
        "fighter_id,first_name,last_name,ufc_id"
    ).is_("photo_url", "null").execute().data
    log.info(f"Fighters missing photos: {len(all_missing)}")

    updated = 0
    failed = 0

    for i, f in enumerate(all_missing, 1):
        fname = f["first_name"]
        lname = f["last_name"]
        log.info(f"[{i}/{len(all_missing)}] {fname} {lname}")

        photo_src, slug = get_photo_url(fname, lname, f.get("ufc_id"))
        if not photo_src:
            log.debug(f"  No photo found on UFC.com")
            failed += 1
            time.sleep(0.3)
            continue

        public_url = download_and_store(f["fighter_id"], photo_src, slug)
        if public_url:
            db.table("fighters").update({
                "photo_url": public_url,
                "ufc_id": slug
            }).eq("fighter_id", f["fighter_id"]).execute()
            updated += 1
            log.info(f"  Stored photo")
        else:
            failed += 1

        time.sleep(0.4)  # polite rate limiting

    log.info(f"Done! Updated={updated} Failed/NotFound={failed}")

if __name__ == "__main__":
    main()