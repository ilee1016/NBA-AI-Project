import json
import re
import argparse
import sqlalchemy as sa
from sqlalchemy import text
from backend.config import DB_DSN, EMBED_MODEL, LLM_MODEL
from backend.utils import ollama_embed, ollama_generate


def retrieve(cx, qvec, k=5):
    sql = """
        SELECT game_id, game_timestamp, home_team_id, away_team_id, home_points, away_points,
               1 - (embedding <=> (:q)::vector) AS score
        FROM game_details
        ORDER BY embedding <-> (:q)::vector
        LIMIT :k
    """
    return cx.execute(text(sql), {"q": qvec, "k": k}).mappings().all()


def build_context(rows):
    lines = []
    for r in rows:
        lines.append(
            f"Game ID {r['game_id']}: {r['home_team_id']} ({r['home_points']}) vs "
            f"{r['away_team_id']} ({r['away_points']}) on {r['game_timestamp']}"
        )
    return "\n".join(lines)


def extract_json(output):
    match = re.search(r"(\[.*\])", output, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return []
    return []


def answer(question, rows, template):
    ctx = build_context(rows)
    prompt = (
        f"Answer the question strictly using this JSON format. "
        f"Do NOT include any text outside the JSON. "
        f"Leave numbers as 0 or strings empty if unknown.\n\n"
        f"Template:\n{json.dumps(template)}\n\n"
        f"Context:\n{ctx}\n\nQ: {question}\nA:"
    )
    raw_output = ollama_generate(LLM_MODEL, prompt)
    return extract_json(raw_output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch RAG runner — answers a list of questions against the NBA database")
    parser.add_argument("--questions", required=True, help="Path to questions JSON file")
    parser.add_argument("--template", required=True, help="Path to answer template JSON file")
    parser.add_argument("--output", required=True, help="Path to write answers JSON")
    parser.add_argument("--k", type=int, default=5, help="Number of games to retrieve per question (default: 5)")
    args = parser.parse_args()

    eng = sa.create_engine(DB_DSN)

    with open(args.questions, encoding="utf-8") as f:
        qs = json.load(f)

    with open(args.template, encoding="utf-8") as f:
        tmpl = json.load(f)

    outs = []
    with eng.begin() as cx:
        for q in qs:
            qvec = ollama_embed(EMBED_MODEL, q["question"])
            rows = retrieve(cx, qvec, args.k)
            ans_json = answer(q["question"], rows, tmpl)
            outs.append({
                "answer": ans_json,
                "evidence": [{"table": "game_details", "id": int(r["game_id"])} for r in rows],
            })

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(outs, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(outs)} answers to {args.output}")
