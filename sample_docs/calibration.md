# Search Calibration Fixture

This file is the input to `backend/scripts/calibrate.py`. It exists to answer one
question with a measurement rather than an assertion: **is the semantic search
actually semantic, and where should the similarity floor sit?**

## Why this exists

The first draft of the plan asserted a similarity floor of `0.25` and a pass mark
of `> 0.4`. Both numbers were invented. MiniLM cosine scores for unrelated text
routinely land in the 0.2–0.3 band, so those constants could have failed a
working system or passed a broken one. Thresholds are now derived from the two
measured distributions below.

## Paraphrase pairs

Each query is a question a real user would ask, worded to share **zero content
words** with the passage that answers it. Keyword search — `LIKE '%...%'`, TF-IDF,
BM25 — cannot connect these. Only an embedding model can. If these rank #1, the
AI requirement is genuinely met; if they do not, no threshold tuning will save it.

| # | Query | Expected source | Overlap with source |
|---|-------|-----------------|---------------------|
| 1 | how long do I have to claim money back after buying something? | `expenses_policy.txt` — "Employees may request reimbursement within 30 days of purchase." | none |
| 2 | can I sleep somewhere expensive when I travel for work? | `expenses_policy.txt` — hotel caps (180 GBP London / 120 GBP elsewhere) | none |
| 3 | how many characters should my login secret be? | `security_policy.txt` — "Passwords must be at least twelve characters long" | none |
| 4 | what happens if my laptop gets taken? | `security_policy.txt` — lost/stolen devices reported within four hours | none |
| 5 | how many days off do new joiners get each year? | `onboarding_guide.pdf` — 25 days paid annual leave | none |
| 6 | how long until I am a permanent member of staff? | `onboarding_guide.pdf` — six month probation | none |
| 7 | am I allowed to do my job from home? | `onboarding_guide.pdf` — remote work up to three days per week | none |

## Control queries

Plausible-sounding, genuinely unanswerable from any document in the corpus. These
measure the **false-positive ceiling**: FAISS always returns its k nearest
neighbours regardless of distance, so without a floor these come back with
confident-looking results that are simply wrong.

| # | Query | Why it must return nothing |
|---|-------|----------------------------|
| 1 | what is the parental leave allowance? | Not covered by any document |
| 2 | how do I file a patent application? | Not covered by any document |
| 3 | what is the company dividend schedule? | Not covered by any document |
| 4 | which vaccinations are required for the office? | Not covered by any document |
| 5 | how do I book the tennis court? | Not covered by any document |

## Reading the result

`calibrate.py` prints the score for every query above, then reports:

- **lowest paraphrase score** — the weakest true positive
- **highest control score** — the strongest false positive
- **separation gap** = lowest paraphrase − highest control

**If the gap is positive**, a floor placed between the two cleanly separates
signal from noise. The script sets `SIMILARITY_FLOOR` to the midpoint.

**If the gap is negative**, the two distributions overlap and *no* floor works:
some real answer scores below some piece of noise. That is a retrieval problem —
fix chunking (size and overlap) and re-measure. Do not paper over an overlap by
picking a threshold; the demo dies the moment the interviewer types their own
paraphrase.

Committed output lives in `calibration_result.md`.
