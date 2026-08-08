import os, json, joblib, datetime, logging
import numpy as np
from pathlib import Path
from huggingface_hub import hf_hub_download

log = logging.getLogger("inference")
_model = None
_explainer = None
_feature_names = None
_loaded_at = None
REPO = os.environ.get("HF_MODEL_REPO", "aramesh129/fightiq-model")

def _load():
    global _model, _explainer, _feature_names, _loaded_at
    log.info("Loading model from HF Hub...")
    model_path     = hf_hub_download(repo_id=REPO, filename="oracle_model.joblib",    repo_type="model")
    explainer_path = hf_hub_download(repo_id=REPO, filename="shap_explainer.joblib",  repo_type="model")
    features_path  = hf_hub_download(repo_id=REPO, filename="feature_names.json",     repo_type="model")
    _model         = joblib.load(model_path)
    _explainer     = joblib.load(explainer_path)
    with open(features_path) as f:
        _feature_names = json.load(f)
    _loaded_at = datetime.datetime.utcnow()
    log.info(f"Model loaded. Features: {len(_feature_names)}")

def get_model():
    global _loaded_at
    if _model is None:
        _load()
    # Hot-reload every hour
    if (datetime.datetime.utcnow() - _loaded_at).seconds > 3600:
        _load()
    return _model, _explainer, _feature_names

def predict(features: list) -> dict:
    model, explainer, feature_names = get_model()
    X = np.array([features])
    proba = model.predict_proba(X)[0]
    red_prob  = float(proba[1])
    blue_prob = float(proba[0])
<<<<<<< HEAD:app/inference.py
    try:                                    
        raw = explainer.shap_values(X)
        sv = np.array(raw)
        if sv.ndim == 3:
            sv = sv[1][0]
        elif sv.ndim == 2:
            sv = sv[0]
        sv = np.array(sv).flatten()[-len(feature_names):]
        shap_dict = {feature_names[i]: float(sv[i]) for i in range(len(feature_names))}
    except Exception as e:
        log.exception(f"SHAP computation failed for input shape {X.shape}: {e}")
        shap_dict = {name: 0.0 for name in feature_names}
=======
    shap_vals = explainer.shap_values(X)
    if isinstance(shap_vals, list):
        sv = shap_vals[1][0]
    else:
        sv = shap_vals[0] if shap_vals.ndim == 3 else shap_vals[0]
    shap_dict = {feature_names[i]: float(sv[i]) for i in range(len(feature_names))}
>>>>>>> d7a3c3c45c0580a568cb3218c61158e7c77c3abb:backend/backend/backend/app/inference.py
    return {
        "red_win_probability":  red_prob,
        "blue_win_probability": blue_prob,
        "shap_values":          shap_dict,
    }