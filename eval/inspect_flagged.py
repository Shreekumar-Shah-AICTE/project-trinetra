import csv
import json
import os

gold = {}
with open("eval/gold_auto.csv") as f:
    reader = csv.DictReader(f)
    for row in reader:
        gold[row["candidate_id"]] = int(row["tier"])

with open("submission.csv") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

# Load candidate details
candidates = {}
with open("../Analysis Material/[PUB] India_runs_data_and_ai_challenge/India_runs_data_and_ai_challenge/candidates.jsonl", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        c = json.loads(line)
        candidates[c["candidate_id"]] = c

print("Ranked Candidates in submission.csv:")
print(f"{'Rank':<5} | {'ID':<12} | {'Gold Tier':<9} | {'Location':<25} | {'Willing Reloc':<13} | {'Current Company / Title'}")
print("-" * 110)
for r in rows[:20]:
    cid = r["candidate_id"]
    tier = gold.get(cid, "UNKNOWN")
    cand = candidates.get(cid, {})
    prof = cand.get("profile", {})
    signals = cand.get("redrob_signals", {})
    location = prof.get("location", "N/A")
    reloc = signals.get("willing_to_relocate", "N/A")
    company = prof.get("current_company", "N/A")
    title = prof.get("current_title", "N/A")
    print(f"{r['rank']:<5} | {cid:<12} | {tier:<9} | {location[:25]:<25} | {str(reloc):<13} | {company[:20]} - {title[:20]}")
