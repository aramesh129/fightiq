import numpy as np
from .database import db

def simulate(bout_id: str, red_id: str, blue_id: str,
             red_prob: float, n: int = 10000) -> dict:
    red_wins = np.random.random(n) < red_prob
    # Get finish rates from fight history
    def finish_rate(fighter_id: str) -> tuple:
        bouts = db.table("bouts").select("winner_id,win_method").or_(
            f"fighter_red_id.eq.{fighter_id},fighter_blue_id.eq.{fighter_id}"
        ).not_.is_("winner_id", "null").execute().data
        wins = [b for b in bouts if b["winner_id"] == fighter_id]
        if not wins: return 0.25, 0.15
        ko  = sum(1 for b in wins if b.get("win_method") and "KO"  in (b["win_method"] or "").upper()) / len(wins)
        sub = sum(1 for b in wins if b.get("win_method") and "SUB" in (b["win_method"] or "").upper()) / len(wins)
        return ko, sub

    red_ko,  red_sub  = finish_rate(red_id)
    blue_ko, blue_sub = finish_rate(blue_id)

    outcomes = []
    for is_red_win in red_wins:
        ko_rate  = red_ko  if is_red_win else blue_ko
        sub_rate = red_sub if is_red_win else blue_sub
        r = np.random.random()
        if r < ko_rate:
            outcomes.append("KO/TKO")
        elif r < ko_rate + sub_rate:
            outcomes.append("Submission")
        else:
            outcomes.append("Decision")

    total = len(outcomes)
    return {
        "ko_probability":         outcomes.count("KO/TKO")    / total,
        "submission_probability": outcomes.count("Submission") / total,
        "decision_probability":   outcomes.count("Decision")   / total,
    }