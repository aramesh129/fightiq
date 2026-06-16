"""
FightIQ Continuous Training Pipeline
Key improvements over the basic version:
  - Exponentially weighted rolling averages
  - Performance trajectory features
  - Red corner bias correction
  - Expanded feature set (29 features)
  - Cross-validation for more reliable evaluation
"""

import os, sys, json, datetime, logging, joblib
import numpy as np
from pathlib import Path
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger("pipeline")
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
db = create_client(os.environ["SUPABASE_URL"],
                   os.environ["SUPABASE_SERVICE_KEY"])

FEATURE_NAMES = [
    # Career differentials
    "slpm_diff", "str_acc_diff", "sapm_diff", "str_def_diff",
    "td_avg_diff", "td_acc_diff", "td_def_diff", "sub_avg_diff",
    # Physical
    "age_diff", "reach_diff", "height_diff",
    # Record quality
    "red_win_pct", "blue_win_pct", "win_pct_diff",
    # Stance
    "red_is_orthodox", "blue_is_orthodox", "stance_mismatch",
    # NEW: Recency-weighted form (last 3 fights, exponentially weighted)
    "red_recent_slpm", "blue_recent_slpm", "recent_slpm_diff",
    "red_recent_sapm", "blue_recent_sapm", "recent_sapm_diff",
    "red_recent_td_def", "blue_recent_td_def",
    # NEW: Trajectory (is fighter trending up or down?)
    "red_sapm_trend", "blue_sapm_trend",
    # NEW: Experience and finish rate
    "red_finish_rate", "blue_finish_rate",
    "total_fights_diff",
]


# ── Stage 1: Load ─────────────────────────────────────────────────────────────

def load_bouts() -> list:
    log.info("Stage 1: Loading bouts...")
    # Load in pages of 1000 to get all bouts
    all_bouts = []
    page_size  = 1000
    offset     = 0
    while True:
        res = db.table("bouts").select(
            "bout_id, fighter_red_id, fighter_blue_id, winner_id, win_method,"
            "events!inner(event_date),"
            "fighter_red:fighters!bouts_fighter_red_id_fkey(*),"
            "fighter_blue:fighters!bouts_fighter_blue_id_fkey(*)"
        ).not_.is_("winner_id", "null").range(offset, offset + page_size - 1).execute()

        if not res.data:
            break
        all_bouts.extend(res.data)
        log.info(f"  Loaded {len(all_bouts)} bouts so far...")
        if len(res.data) < page_size:
            break
        offset += page_size

    log.info(f"  Total: {len(all_bouts)} completed bouts")
    return all_bouts

# ── Per-fighter historical stats (for trajectory calculation) ─────────────────

_fighter_history_cache: dict = {}

def get_fighter_history(fighter_id: str) -> list:
    """
    Returns a fighter's last 8 bouts sorted newest-first,
    with their fight_stats for each bout.
    Cached to avoid repeated DB calls during feature engineering.
    """
    if fighter_id in _fighter_history_cache:
        return _fighter_history_cache[fighter_id]

    res = db.table("bouts").select(
        "bout_id, winner_id, fighter_red_id, fighter_blue_id, win_method,"
        "events!inner(event_date),"
        "fight_stats(*)"
    ).or_(
        f"fighter_red_id.eq.{fighter_id},fighter_blue_id.eq.{fighter_id}"
    ).not_.is_("winner_id", "null").order("created_at", desc=True).limit(8).execute()

    _fighter_history_cache[fighter_id] = res.data
    return res.data


# ── Feature helpers ───────────────────────────────────────────────────────────

def _age(f) -> float:
    b = f.get("birthday")
    if not b: return 28.0
    try:
        return (datetime.date.today() -
                datetime.date.fromisoformat(str(b)[:10])).days / 365.25
    except: return 28.0

def _wp(f) -> float:
    w = f.get("wins", 0) or 0
    l = f.get("losses", 0) or 0
    return w / (w + l) if (w + l) > 0 else 0.5

def _total_fights(f) -> int:
    return (f.get("wins", 0) or 0) + (f.get("losses", 0) or 0)

def _finish_rate(fighter_id: str) -> float:
    """Proportion of wins that were finishes (KO/TKO or Submission)."""
    history = get_fighter_history(fighter_id)
    wins = [b for b in history if b.get("winner_id") == fighter_id]
    if not wins: return 0.5
    finishes = sum(1 for b in wins
                   if b.get("win_method") and
                   any(m in (b["win_method"] or "").upper()
                       for m in ["KO", "TKO", "SUBMISSION", "SUB"]))
    return finishes / len(wins)

def _exponential_weights(n: int, decay: float = 0.7) -> list:
    """
    Returns exponential weights summing to 1.
    Most recent fight gets the highest weight.
    decay=0.7 means each older fight counts as 70% of the next more recent one.
    """
    if n == 0: return []
    weights = [decay ** i for i in range(n)]
    total   = sum(weights)
    return [w / total for w in weights]

def _weighted_stat(bouts: list, fighter_id: str,
                   stat_key: str, total_mins: float = 15.0) -> float:
    """
    Computes an exponentially weighted average of a per-fight stat.
    Weights recent bouts more heavily than older ones.
    """
    values  = []
    for bout in bouts:
        stats_list = bout.get("fight_stats") or []
        stat = next((s for s in stats_list
                     if s.get("fighter_id") == fighter_id), None)
        if not stat: continue
        if stat_key == "slpm":
            landed = stat.get("sig_str_landed", 0) or 0
            values.append(landed / total_mins)
        elif stat_key == "sapm":
            absorbed = stat.get("sig_str_attempted", 0) or 0
            values.append(absorbed / total_mins)
        elif stat_key == "td_def":
            tda = stat.get("td_attempted", 0) or 0
            tdl = stat.get("td_landed",    0) or 0
            # TD defense = opponent's TD accuracy = how often they succeeded
            values.append((tdl / tda) if tda > 0 else 0.65)

    if not values: return 0.0
    weights = _exponential_weights(len(values))
    return sum(v * w for v, w in zip(values, weights))

def _sapm_trend(bouts: list, fighter_id: str) -> float:
    """
    Positive = fighter is absorbing MORE strikes recently (declining defense).
    Negative = fighter is absorbing FEWER strikes recently (improving defense).
    Computed as: recent_3_avg - older_avg, normalized.
    """
    values = []
    for bout in bouts:
        stats_list = bout.get("fight_stats") or []
        stat = next((s for s in stats_list
                     if s.get("fighter_id") == fighter_id), None)
        if not stat: continue
        a = stat.get("sig_str_attempted", 0) or 0
        values.append(a / 15.0)

    if len(values) < 4: return 0.0
    recent = np.mean(values[:3])   # last 3 fights
    older  = np.mean(values[3:])   # older fights
    return float(recent - older)


# ── Core feature engineering ──────────────────────────────────────────────────

def engineer(red: dict, blue: dict, bout_date: str = None) -> list:
    def s(v): return float(v) if v is not None else 0.0

    # Career average differentials
    career = [
        s(red.get("slpm"))    - s(blue.get("slpm")),
        s(red.get("str_acc")) - s(blue.get("str_acc")),
        s(red.get("sapm"))    - s(blue.get("sapm")),
        s(red.get("str_def")) - s(blue.get("str_def")),
        s(red.get("td_avg"))  - s(blue.get("td_avg")),
        s(red.get("td_acc"))  - s(blue.get("td_acc")),
        s(red.get("td_def"))  - s(blue.get("td_def")),
        s(red.get("sub_avg")) - s(blue.get("sub_avg")),
        _age(red) - _age(blue),
        s(red.get("reach_cm"))  - s(blue.get("reach_cm")),
        s(red.get("height_cm")) - s(blue.get("height_cm")),
        _wp(red), _wp(blue), _wp(red) - _wp(blue),
        1.0 if red.get("stance")  == "Orthodox" else 0.0,
        1.0 if blue.get("stance") == "Orthodox" else 0.0,
        1.0 if red.get("stance")  != blue.get("stance") else 0.0,
    ]

    # Recent form (exponentially weighted, last 8 fights)
    red_history  = get_fighter_history(red["fighter_id"])
    blue_history = get_fighter_history(blue["fighter_id"])

    red_r_slpm   = _weighted_stat(red_history,  red["fighter_id"],  "slpm")
    blue_r_slpm  = _weighted_stat(blue_history, blue["fighter_id"], "slpm")
    red_r_sapm   = _weighted_stat(red_history,  red["fighter_id"],  "sapm")
    blue_r_sapm  = _weighted_stat(blue_history, blue["fighter_id"], "sapm")
    red_r_tddef  = _weighted_stat(red_history,  red["fighter_id"],  "td_def")
    blue_r_tddef = _weighted_stat(blue_history, blue["fighter_id"], "td_def")

    recent = [
        red_r_slpm,  blue_r_slpm,  red_r_slpm  - blue_r_slpm,
        red_r_sapm,  blue_r_sapm,  red_r_sapm  - blue_r_sapm,
        red_r_tddef, blue_r_tddef,
    ]

    # Trajectory and finish rate
    meta = [
        _sapm_trend(red_history,  red["fighter_id"]),
        _sapm_trend(blue_history, blue["fighter_id"]),
        _finish_rate(red["fighter_id"]),
        _finish_rate(blue["fighter_id"]),
        float(_total_fights(red) - _total_fights(blue)),
    ]

    return career + recent + meta


# ── Stage 2: Build matrix ────────────────────────────────────────────────────

def build_matrix(bouts):
    """
    Builds feature matrix from pre-loaded bout data.
    Since winner_id always = fighter_red_id in our DB (due to ufcstats ordering),
    we randomly flip 50% of bouts so the model sees both classes.
    """
    global _fighter_history_cache
    _fighter_history_cache = {}
    import random
    random.seed(42)

    X, y, dates = [], [], []
    skipped = 0

    for b in bouts:
        try:
            red  = b["fighter_red"]
            blue = b["fighter_blue"]

            # Randomly flip fighters so model sees both red-wins and blue-wins
            # This is valid because the model learns from stat differentials,
            # not from red/blue corner assignment
            if random.random() < 0.5:
                # Keep as-is: red = winner (label 1)
                feats = engineer(red, blue)
                label = 1
            else:
                # Flip: blue perspective, so blue stats go first = loser (label 0)
                feats = engineer(blue, red)
                label = 0

            edate = (b.get("events") or {}).get("event_date", "2000-01-01")
            X.append(feats)
            y.append(label)
            dates.append(edate)
        except Exception as e:
            skipped += 1
            continue

    log.info(f"  Matrix: {len(X)} samples × {len(X[0]) if X else 0} features "
             f"(skipped {skipped})")
    return np.array(X), np.array(y), dates


# ── Stage 3: Update rolling stats (exponentially weighted) ───────────────────

def update_rolling_stats():
    """
    Updates each fighter's career-average stats using exponentially
    weighted averages of their fight_stats rows — recent fights matter more.
    """
    log.info("Stage 2a: Updating rolling stats (exponential weighting)...")
    fighters = db.table("fighters").select("fighter_id").execute().data
    updated  = 0
    for f in fighters:
        fid     = f["fighter_id"]
        history = get_fighter_history(fid)
        if not history: continue
        n    = len(history)
        wts  = _exponential_weights(n)
        mins = 15.0

        slpm_vals = []; sapm_vals = []; td_vals = []
        str_acc_vals = []; td_acc_vals = []

        for bout in history:
            stats_list = bout.get("fight_stats") or []
            stat = next((s for s in stats_list if s.get("fighter_id") == fid), None)
            if not stat: continue
            sl  = stat.get("sig_str_landed",    0) or 0
            sa  = stat.get("sig_str_attempted", 0) or 0
            ab  = stat.get("total_str_landed",  0) or 0
            tdl = stat.get("td_landed",    0) or 0
            tda = stat.get("td_attempted", 0) or 0
            slpm_vals.append(sl / mins)
            sapm_vals.append(ab / mins)
            if sa  > 0: str_acc_vals.append(sl  / sa)
            if tda > 0: td_acc_vals.append(tdl / tda)
            td_vals.append(tdl / mins)

        def wavg(vals):
            w = _exponential_weights(len(vals))
            return round(sum(v * ww for v, ww in zip(vals, w)), 4) if vals else None

        upd = {}
        if slpm_vals:    upd["slpm"]    = wavg(slpm_vals)
        if sapm_vals:    upd["sapm"]    = wavg(sapm_vals)
        if str_acc_vals: upd["str_acc"] = wavg(str_acc_vals)
        if td_acc_vals:  upd["td_acc"]  = wavg(td_acc_vals)
        if td_vals:      upd["td_avg"]  = wavg(td_vals)
        if upd:
            db.table("fighters").update(upd).eq("fighter_id", fid).execute()
            updated += 1

    log.info(f"  Updated {updated} fighters (exp. weighted)")


def update_records():
    log.info("Stage 2b: W/L records...")
    db.rpc("recalculate_fighter_records", {}).execute()

def update_photos():
    import requests as rq
    from bs4 import BeautifulSoup
    log.info("Stage 2c: Photos (30 per run)...")
    fighters = db.table("fighters").select(
        "fighter_id,first_name,last_name,ufc_id"
    ).is_("photo_url", "null").limit(30).execute().data
    hdrs = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.ufc.com/",
    }
    updated = 0
    for f in fighters:
        slug = f.get("ufc_id") or (
            f"{f['first_name']}-{f['last_name']}"
            .lower().replace(" ", "-").replace("'", "").replace(".", ""))
        try:
            page = rq.get(f"https://www.ufc.com/athlete/{slug}",
                          headers={"User-Agent": hdrs["User-Agent"]}, timeout=12)
            if page.status_code != 200: continue
            soup = BeautifulSoup(page.text, "html.parser")
            img  = (soup.select_one("img.hero-profile__image")
                    or soup.select_one(".c-bio__image img")
                    or soup.select_one('img[src*="/athlete/"]'))
            if not img: continue
            raw = img.get("src") or img.get("data-src", "")
            if not raw or "placeholder" in raw.lower(): continue
            if raw.startswith("//"): raw = "https:" + raw
            elif raw.startswith("/"): raw = "https://www.ufc.com" + raw
            ir = rq.get(raw, headers=hdrs, timeout=15)
            if ir.status_code != 200: continue
            ct   = ir.headers.get("content-type", "image/jpeg")
            ext  = "jpg" if "jpeg" in ct else ct.split("/")[-1].split(";")[0]
            path = f"{f['fighter_id']}.{ext}"
            db.storage.from_("fighter-photos").upload(
                path, ir.content,
                file_options={"content-type": ct, "upsert": "true"})
            url = db.storage.from_("fighter-photos").get_public_url(path)
            db.table("fighters").update(
                {"photo_url": url, "ufc_id": slug}
            ).eq("fighter_id", f["fighter_id"]).execute()
            updated += 1
        except Exception as e:
            log.debug(f"Photo failed {slug}: {e}")
    log.info(f"  Updated {updated} photos")


# ── Stage 4: Train ───────────────────────────────────────────────────────────

def train(X, y, dates):
    from sklearn.ensemble import (RandomForestClassifier,
                                   GradientBoostingClassifier, VotingClassifier)
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
    from sklearn.metrics import (accuracy_score, brier_score_loss,
                                  log_loss, roc_auc_score)

    log.info("Stage 4: Training...")
    log.info(f"  Total samples: {len(X)}, Class distribution: {sum(y)}/{len(y)-sum(y)} (red wins/blue wins)")

    # Always use random split — time split fails with small recent datasets
    Xtr, Xte, ytr, yte = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)
    log.info(f"  Train={len(Xtr)}  Test={len(Xte)}")

    rf  = RandomForestClassifier(
        n_estimators=400, max_depth=10, min_samples_leaf=4,
        max_features="sqrt", random_state=42, n_jobs=-1)
    gbm = GradientBoostingClassifier(
        n_estimators=300, max_depth=4, learning_rate=0.03,
        subsample=0.8, random_state=42)
    lr  = Pipeline([
        ("s", StandardScaler()),
        ("lr", LogisticRegression(C=0.5, max_iter=2000,
                                   class_weight="balanced", random_state=42))
    ])

    ens = VotingClassifier(
        estimators=[("rf", rf), ("gbm", gbm), ("lr", lr)],
        voting="soft", weights=[2, 2, 1])
    cal = CalibratedClassifierCV(ens, cv=3, method="sigmoid")
    cal.fit(Xtr, ytr)

    yp  = cal.predict(Xte)
    ypr = cal.predict_proba(Xte)[:, 1]
    m   = {
        "accuracy":    float(accuracy_score(yte, yp)),
        "brier_score": float(brier_score_loss(yte, ypr)),
        "log_loss":    float(log_loss(yte, ypr)),
        "roc_auc":     float(roc_auc_score(yte, ypr)),
        "train_size":  len(Xtr),
        "test_size":   len(Xte),
        "trained_at":  datetime.datetime.utcnow().isoformat(),
    }
    log.info(f"  acc={m['accuracy']:.3f}  brier={m['brier_score']:.3f}"
             f"  auc={m['roc_auc']:.3f}")

    # 3-fold CV
    log.info("  Running 3-fold CV...")
    cv_scores = cross_val_score(cal, X, y, cv=StratifiedKFold(3),
                                 scoring="accuracy", n_jobs=1)
    m["cv_accuracy_mean"] = float(cv_scores.mean())
    m["cv_accuracy_std"]  = float(cv_scores.std())
    log.info(f"  CV: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

    return cal, m

# ── Stage 5: SHAP explainer (correct path) ───────────────────────────────────

def build_explainer(cal_model):
    import shap
    voting   = cal_model.calibrated_classifiers_[0].estimator
    rf_model = None
    for item in voting.estimators_:
        # estimators_ can be (name, est) tuples or just estimators
        est = item[1] if isinstance(item, tuple) else item
        if hasattr(est, "n_estimators"):
            rf_model = est; break
        if hasattr(est, "named_steps"):
            inner = list(est.named_steps.values())[0]
            if hasattr(inner, "n_estimators"):
                rf_model = inner; break
    if rf_model is None:
        raise RuntimeError("Could not find RF in ensemble")
    return shap.TreeExplainer(rf_model)


# ── Stage 6: Performance gate ────────────────────────────────────────────────

def load_prod_metrics() -> dict:
    try:
        res = db.table("model_versions").select("*").order(
            "deployed_at", desc=True).limit(1).execute()
        if res.data: return res.data[0]
    except: pass
    return {"accuracy": 0.0, "brier_score": 1.0}

def should_deploy(cand: dict, prod: dict) -> tuple[bool, str]:
    if cand["accuracy"] < 0.58:
        return False, f"ABORT: acc {cand['accuracy']:.3f} < 0.58 minimum"
    if cand["accuracy"] < prod.get("accuracy", 0.0) - 0.01:
        return False, f"ABORT: regressed {cand['accuracy']:.3f} < {prod['accuracy']:.3f}"
    if cand["brier_score"] > prod.get("brier_score", 1.0) * 1.10:
        return False, f"ABORT: brier degraded {cand['brier_score']:.3f}"
    return True, f"PASS: {cand['accuracy']:.3f} >= {prod.get('accuracy', 0.0):.3f}"


# ── Stage 7: Deploy ──────────────────────────────────────────────────────────

def deploy(model, metrics: dict, explainer):
    from huggingface_hub import HfApi
    log.info("Stage 7: Deploying...")
    Path("model_artifacts").mkdir(exist_ok=True)
    version = f"v{datetime.date.today().strftime('%Y%m%d')}"
    metrics["model_version"] = version
    joblib.dump(model,     "model_artifacts/oracle_model.joblib")
    joblib.dump(explainer, "model_artifacts/shap_explainer.joblib")
    with open("model_artifacts/feature_names.json", "w") as f:
        json.dump(FEATURE_NAMES, f)
    with open("model_artifacts/metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    repo = os.environ["HF_MODEL_REPO"]
    api  = HfApi(token=os.environ["HF_TOKEN"])
    try: api.create_repo(repo_id=repo, repo_type="model", exist_ok=True)
    except: pass
    for fname in ["oracle_model.joblib", "shap_explainer.joblib",
                  "feature_names.json", "metrics.json"]:
        api.upload_file(
            path_or_fileobj=f"model_artifacts/{fname}",
            path_in_repo=fname, repo_id=repo, repo_type="model",
            commit_message=f"FightIQ {version} acc={metrics['accuracy']:.3f}")
    db.table("model_versions").insert({
        "version":    version,
        "accuracy":   metrics["accuracy"],
        "brier_score":metrics["brier_score"],
        "log_loss":   metrics["log_loss"],
        "roc_auc":    metrics["roc_auc"],
        "train_size": metrics["train_size"],
        "test_size":  metrics["test_size"],
    }).execute()
    try:
        api.restart_space(repo_id=os.environ["HF_SPACE_NAME"])
        log.info("  Space restarted")
    except Exception as e:
        log.warning(f"  Space restart failed (non-critical): {e}")
    log.info(f"  Deployed {version}")


# ── Main ─────────────────────────────────────────────────────────────────────

def run():
    log.info("=" * 60)
    log.info("FightIQ Improved Pipeline")
    bouts = load_bouts()
    if len(bouts) < 100:
        log.error("Not enough bouts — run backfill.py 2001 first")
        sys.exit(1)
    update_rolling_stats()
    update_records()
    update_photos()
    X, y, dates = build_matrix(bouts)
    log.info(f"  y class counts: {sum(y)} red wins, {len(y)-sum(y)} blue wins out of {len(y)} total")
    model, metrics = train(X, y, dates)
    explainer = build_explainer(model)
    prod = load_prod_metrics()
    ok, reason = should_deploy(metrics, prod)
    log.info(f"Gate: {reason}")
    if ok:
        deploy(model, metrics, explainer)
    else:
        log.warning("Not deployed — keeping current version")

if __name__ == "__main__":
    run()