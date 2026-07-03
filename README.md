# FightIQ 

AI UFC fight prediction platform built with a calibrated ensemble model, real-time scraping, and automated weekly retraining.

**Live site**: [fightiq-woad.vercel.app](https://fightiq-woad.vercel.app)

--

## What it does

- Predicts UFC fight outcomes with **78% accuracy** using a calibrated voting ensemble
- Shows win probabilities, Monte Carlo outcome distributions, and SHAP feature attribution for every fight
- Automatically scrapes new events, retrains the model, and generates predictions every week

--

## Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 14, deployed on Vercel |
| Backend | FastAPI, deployed on Hugging Face Spaces |
| Database | Supabase (PostgreSQL) |
| Model | scikit-learn ensemble, hosted on Hugging Face Hub |
| Automation | GitHub Actions (weekly) |
| Uptime | UptimeRobot |

---

## Model

**Architecture**: Calibrated Voting Ensemble
- Random Forest (400 trees) — weight 2
- Gradient Boosting (300 estimators) — weight 2
- Logistic Regression — weight 1

**Performance**:
- Accuracy: 78.0%
- ROC AUC: 0.872
- Brier Score: 0.148
- Trained on 6,841 fights

**Features (30 total)**:
- Career stat differentials (SLpM, SApM, TD%, strike accuracy, submission avg)
- Physical differentials (age, reach, height)
- Win percentage and record
- Exponentially weighted recent form (last 3–5 fights)
- Performance trajectory (SApM trend)
- Finish rates
- Stance matchup indicators

**Explainability**: SHAP TreeExplainer on Random Forest base model

--

## Automation

Every Monday at 10am UTC, GitHub Actions runs:
1. **Scraper** — settles completed events, loads upcoming cards from ufcstats.com
2. **Continuous training** — retrains model if new data passes performance gate, deploys to HF Hub
3. **Prediction generation** — generates win probabilities and Monte Carlo simulations for all upcoming bouts

--

