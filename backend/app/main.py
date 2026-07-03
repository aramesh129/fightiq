import os, datetime, logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .database import db
from .inference import predict, get_model
from .monte_carlo import simulate

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("main")

app = FastAPI(title="FightIQ API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def engineer_features(red: dict, blue: dict) -> list:
    def s(v): return float(v) if v is not None else 0.0
    def age(f):
        b = f.get("birthday")
        if not b: return 28.0
        try:
            return (datetime.date.today() -
                    datetime.date.fromisoformat(str(b)[:10])).days / 365.25
        except: return 28.0
    def wp(f):
        w = f.get("wins", 0) or 0
        l = f.get("losses", 0) or 0
        return w / (w + l) if (w + l) > 0 else 0.5

    career = [
        s(red.get("slpm"))    - s(blue.get("slpm")),
        s(red.get("str_acc")) - s(blue.get("str_acc")),
        s(red.get("sapm"))    - s(blue.get("sapm")),
        s(red.get("str_def")) - s(blue.get("str_def")),
        s(red.get("td_avg"))  - s(blue.get("td_avg")),
        s(red.get("td_acc"))  - s(blue.get("td_acc")),
        s(red.get("td_def"))  - s(blue.get("td_def")),
        s(red.get("sub_avg")) - s(blue.get("sub_avg")),
        age(red) - age(blue),
        s(red.get("reach_cm"))  - s(blue.get("reach_cm")),
        s(red.get("height_cm")) - s(blue.get("height_cm")),
        wp(red), wp(blue), wp(red) - wp(blue),
        1.0 if red.get("stance")  == "Orthodox" else 0.0,
        1.0 if blue.get("stance") == "Orthodox" else 0.0,
        1.0 if red.get("stance")  != blue.get("stance") else 0.0,
    ]
    # Recent form placeholders (pipeline fills these; API uses career stats)
    recent = [0.0] * 8
    meta   = [0.0, 0.0,
              len([b for b in [] if True]) / max(1, (red.get("wins",0) or 0) + (red.get("losses",0) or 0)),
              len([b for b in [] if True]) / max(1, (blue.get("wins",0) or 0) + (blue.get("losses",0) or 0)),
              float(((red.get("wins",0) or 0) + (red.get("losses",0) or 0)) -
                    ((blue.get("wins",0) or 0) + (blue.get("losses",0) or 0)))]
    return career + recent + meta

@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.datetime.utcnow().isoformat()}

@app.get("/api/upcoming")
def upcoming():
    res = db.table("upcoming_card").select("*").execute()
    return res.data

@app.get("/api/fight/{bout_id}")
def fight_detail(bout_id: str):
    bout = db.table("bouts").select(
        "*,events(*),fighter_red:fighters!bouts_fighter_red_id_fkey(*),"
        "fighter_blue:fighters!bouts_fighter_blue_id_fkey(*),"
        "predictions(*),fight_stats(*)"
    ).eq("bout_id", bout_id).single().execute()
    if not bout.data:
        raise HTTPException(404, "Bout not found")
    return bout.data

@app.get("/api/fighter/{fighter_id}")
def fighter_detail(fighter_id: str):
    fighter = db.table("fighters").select("*").eq(
        "fighter_id", fighter_id).single().execute()
    if not fighter.data:
        raise HTTPException(404, "Fighter not found")
    history = db.table("bouts").select(
        "*,events(*),fighter_red:fighters!bouts_fighter_red_id_fkey(first_name,last_name),"
        "fighter_blue:fighters!bouts_fighter_blue_id_fkey(first_name,last_name)"
    ).or_(
        f"fighter_red_id.eq.{fighter_id},fighter_blue_id.eq.{fighter_id}"
    ).not_.is_("winner_id","null").order("created_at", desc=True).limit(20).execute()
    return {"fighter": fighter.data, "history": history.data}

@app.get("/api/history")
def history(page: int = 1, limit: int = 20):
    offset = (page - 1) * limit
    res = db.table("bouts").select(
        "*,events(*),fighter_red:fighters!bouts_fighter_red_id_fkey(first_name,last_name,photo_url),"
        "fighter_blue:fighters!bouts_fighter_blue_id_fkey(first_name,last_name,photo_url),"
        "predictions(*)"
    ).not_.is_("winner_id","null").order("event_id", desc=True).range(offset, offset+limit-1).execute()
    
    # Sort by event_date desc in Python since Supabase can't order by joined columns
    data = res.data
    data.sort(key=lambda x: x.get("events", {}).get("event_date", "") if x.get("events") else "", reverse=True)
    return data

@app.get("/api/stats")
def model_stats():
    versions = db.table("model_versions").select("*").order(
        "deployed_at", desc=True).limit(10).execute()
    return versions.data

@app.post("/api/generate-predictions")
def generate_predictions():
    # Get all upcoming event IDs
    events = db.table("events").select("event_id").eq(
        "is_completed", False).execute().data
    event_ids = [e["event_id"] for e in events]

    if not event_ids:
        return {"generated": 0, "reason": "no upcoming events"}

    # Get all bouts for upcoming events
    all_bouts = []
    for eid in event_ids:
        res = db.table("bouts").select(
            "bout_id, fighter_red_id, fighter_blue_id,"
            "fighter_red:fighters!bouts_fighter_red_id_fkey(*),"
            "fighter_blue:fighters!bouts_fighter_blue_id_fkey(*)"
        ).eq("event_id", eid).execute()
        all_bouts.extend(res.data)

    # Skip bouts that already have predictions
    existing = {r["bout_id"] for r in
                db.table("predictions").select("bout_id").execute().data}

    generated = 0
    for bout in all_bouts:
        if bout["bout_id"] in existing:
            continue
        red  = bout["fighter_red"]
        blue = bout["fighter_blue"]
        if not red or not blue:
            continue
        try:
            features = engineer_features(red, blue)
            pred     = predict(features)
            mc       = simulate(bout["bout_id"], bout["fighter_red_id"],
                                bout["fighter_blue_id"],
                                pred["red_win_probability"])
            db.table("predictions").upsert({
                "bout_id":                bout["bout_id"],
                "predicted_winner_id":    bout["fighter_red_id"]
                                          if pred["red_win_probability"] > 0.5
                                          else bout["fighter_blue_id"],
                "red_win_probability":    pred["red_win_probability"],
                "blue_win_probability":   pred["blue_win_probability"],
                "ko_probability":         mc["ko_probability"],
                "submission_probability": mc["submission_probability"],
                "decision_probability":   mc["decision_probability"],
                "shap_values":            pred["shap_values"],
                "model_version":          "v20260615",
            }, on_conflict="bout_id").execute()
            generated += 1
        except Exception as e:
            import traceback
            log.warning(f"Prediction failed {bout['bout_id']}: {e}")
            log.warning(traceback.format_exc())

    return {"generated": generated}