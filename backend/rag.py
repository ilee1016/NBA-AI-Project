import os
import json
import re
import sqlalchemy as sa
from sqlalchemy import text
from backend.config import DB_DSN, EMBED_MODEL, LLM_MODEL
from backend.utils import ollama_embed, ollama_generate

BASE_DIR = os.path.dirname(__file__)
QUESTIONS_PATH = os.path.normpath(os.path.join(BASE_DIR, "..", "part1", "questions.json"))
ANSWERS_PATH = os.path.normpath(os.path.join(BASE_DIR, "..", "part1", "answers.json"))
TEMPLATE_PATH = os.path.normpath(os.path.join(BASE_DIR, "..", "part1", "answers_template.json"))


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
    """Build readable multi-line summaries of retrieved games."""
    lines = []
    for r in rows:
        lines.append(
            f"Game ID {r['game_id']}: {r['home_team_id']} ({r['home_points']}) vs {r['away_team_id']} ({r['away_points']}) on {r['game_timestamp']}"
        )
    return "\n".join(lines)


def extract_json(output):
    """Extract JSON array from LLM output."""
    match = re.search(r"(\[.*\])", output, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return []
    return []


def answer(question, rows):
    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        answers_template = json.load(f)

    ctx = build_context(rows)

    prompt = (
        f"Answer the question strictly using this JSON format. "
        f"Do NOT include any text outside the JSON. "
        f"Leave numbers as 0 or strings empty if unknown.\n\n"
        f"Template:\n{json.dumps(answers_template)}\n\n"
        f"Context:\n{ctx}\n\nQ: {question}\nA:"
    )

    raw_output = ollama_generate(LLM_MODEL, prompt)
    return extract_json(raw_output)


if __name__ == "__main__":
    eng = sa.create_engine(DB_DSN)

    with open(QUESTIONS_PATH, encoding="utf-8") as f:
        qs = json.load(f)

    outs = []
    with eng.begin() as cx:
        for q in qs:
            qvec = ollama_embed(EMBED_MODEL, q["question"])
            rows = retrieve(cx, qvec, 5)
            ans_json = answer(q["question"], rows)
            outs.append({
                "answer": ans_json,
                "evidence": [{"table": "game_details", "id": int(r["game_id"])} for r in rows],
            })

    with open(ANSWERS_PATH, "w", encoding="utf-8") as f:
        json.dump(outs, f, ensure_ascii=False, indent=2)