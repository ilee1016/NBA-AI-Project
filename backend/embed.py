import pandas as pd
import sqlalchemy as sa
from sqlalchemy import text
from backend.config import DB_DSN, EMBED_MODEL
from backend.utils import ollama_embed


def row_text(r):
    ts = pd.to_datetime(r.game_timestamp, utc=True)
    date = ts.strftime('%Y-%m-%d')
    season = int(r.season)
    hp = int(r.home_points)
    ap = int(r.away_points)

    if hp > ap:
        result_line = f"({hp}) W {r.home_team} vs {r.away_team} L ({ap})"
    elif ap > hp:
        result_line = f"({hp}) L {r.home_team} vs {r.away_team} W ({ap})"
    else:
        result_line = f"({hp}) {r.home_team} vs {r.away_team} ({ap}) Tie"

    return (
        f"Season: {season}\n"
        f"Date: {date}\n"
        f"{result_line}"
    )


def main():
    print("Starting Embedding Process")
    eng = sa.create_engine(DB_DSN)
    with eng.begin() as cx:
        cx.execute(text("ALTER DATABASE nba REFRESH COLLATION VERSION"))
        cx.execute(text("ALTER TABLE IF EXISTS game_details ADD COLUMN IF NOT EXISTS embedding vector(768);"))
        cx.execute(text("CREATE INDEX IF NOT EXISTS idx_game_details_embedding ON game_details USING hnsw (embedding vector_cosine_ops);"))

        query = """
        SELECT 
            gd.game_id,
            gd.season,
            gd.game_timestamp,
            CONCAT(ht.city, ' ', ht.name) AS home_team,
            CONCAT(at.city, ' ', at.name) AS away_team,
            gd.home_points,
            gd.away_points
        FROM game_details gd
        JOIN teams ht ON gd.home_team_id = ht.team_id
        JOIN teams at ON gd.away_team_id = at.team_id
        ORDER BY gd.game_timestamp DESC, gd.game_id DESC
        """

        df = pd.read_sql(query, cx)

        for _, r in df.iterrows():
            vec = ollama_embed(EMBED_MODEL, row_text(r))
            cx.execute(
                text("UPDATE game_details SET embedding = :v WHERE game_id = :gid"),
                {"v": vec, "gid": int(r.game_id)}
            )

    print(f"Finished Embeddings: {len(df)} Rows Updated")


if __name__ == "__main__":
    main()