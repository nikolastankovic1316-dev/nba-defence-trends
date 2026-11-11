import json, os, time
from datetime import datetime, timezone
import pandas as pd
from nba_api.stats.endpoints import playergamelogs, commonteamroster
from nba_api.stats.static import teams

SEASON = os.getenv("NBA_SEASON", "2026-27")
SEASON_TYPE = os.getenv("NBA_SEASON_TYPE", "Regular Season")
OUT = "data/data.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Referer": "https://www.nba.com/", "Origin": "https://www.nba.com"
}

def retry_call(fn, label, attempts=4):
    last = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:
            last = exc
            wait = 3 * (i + 1)
            print(f"{label} failed ({i+1}/{attempts}): {exc}; waiting {wait}s", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"{label} failed after {attempts} attempts: {last}")

def position_group(raw):
    p = str(raw or "").upper().strip()
    if p.startswith("G"): return "Guards"
    if p.startswith("C"): return "Centers"
    if p.startswith("F"): return "Forwards"
    return "Unknown"

def get_roster_positions():
    mapping = {}
    for team in teams.get_teams():
        def fetch(team_id=team["id"]):
            return commonteamroster.CommonTeamRoster(team_id=team_id, season=SEASON, timeout=35, headers=HEADERS).get_data_frames()[0]
        try:
            roster = retry_call(fetch, "roster " + team["abbreviation"])
            if not roster.empty:
                for _, row in roster.iterrows():
                    mapping[str(row["PLAYER_ID"])] = position_group(row.get("POSITION"))
        except Exception as exc:
            print(f"WARNING: roster unavailable for {team['abbreviation']}: {exc}", flush=True)
        time.sleep(0.8)
    return mapping

def get_player_logs():
    def fetch():
        endpoint = playergamelogs.PlayerGameLogs(
            league_id_nullable="00", season_nullable=SEASON,
            season_type_nullable=SEASON_TYPE, player_id_nullable="",
            team_id_nullable="", date_from_nullable="", date_to_nullable="",
            last_n_games_nullable="0", measure_type_player_game_logs_nullable="Base",
            per_mode_simple_nullable="PerGame", timeout=60, headers=HEADERS
        )
        return endpoint.get_data_frames()[0]
    return retry_call(fetch, "league player game logs")

def main():
    os.makedirs("data", exist_ok=True)
    print(f"Fetching NBA {SEASON} {SEASON_TYPE} player game logs", flush=True)
    logs = get_player_logs()
    if logs.empty:
        raise RuntimeError("NBA returned an empty player game log. Existing data will not be overwritten.")
    positions = get_roster_positions()
    logs["PLAYER_ID"] = logs["PLAYER_ID"].astype(str)
    logs["position"] = logs["PLAYER_ID"].map(positions).fillna("Unknown")
    logs["opponent"] = logs["MATCHUP"].astype(str).str.extract(r"(?:vs\\.|@)\\s*([A-Z]{2,3})$", expand=False)
    logs["GAME_DATE"] = pd.to_datetime(logs["GAME_DATE"], errors="coerce")
    logs = logs.dropna(subset=["GAME_DATE", "opponent"])
    for col in ["PTS", "REB", "AST", "FG3M", "MIN"]:
        logs[col] = pd.to_numeric(logs[col], errors="coerce").fillna(0)
    logs["PRA"] = logs["PTS"] + logs["REB"] + logs["AST"]
    player_rows = []
    for _, r in logs.iterrows():
        player_rows.append({
            "player": str(r["PLAYER_NAME"]), "player_id": str(r["PLAYER_ID"]),
            "team": str(r["TEAM_ABBREVIATION"]), "opponent": str(r["opponent"]),
            "date": r["GAME_DATE"].strftime("%Y-%m-%d"), "position": str(r["position"]),
            "pts": round(float(r["PTS"]),1), "reb": round(float(r["REB"]),1),
            "ast": round(float(r["AST"]),1), "pra": round(float(r["PRA"]),1),
            "fg3m": round(float(r["FG3M"]),1), "min": round(float(r["MIN"]),1),
            "game_id": str(r["GAME_ID"])
        })
    known = logs[logs["position"].isin(["Guards","Forwards","Centers"])].copy()
    defense = []
    if not known.empty:
        grouped = known.groupby(["opponent","position"]).agg(
            games=("GAME_ID","nunique"), player_games=("PLAYER_ID","count"),
            pts=("PTS","mean"), reb=("REB","mean"), ast=("AST","mean"),
            pra=("PRA","mean"), fg3m=("FG3M","mean")
        ).reset_index()
        for _, r in grouped.iterrows():
            defense.append({
                "team":str(r["opponent"]), "position":str(r["position"]),
                "games":int(r["games"]), "player_games":int(r["player_games"]),
                "pts":round(float(r["pts"]),2), "reb":round(float(r["reb"]),2),
                "ast":round(float(r["ast"]),2), "pra":round(float(r["pra"]),2),
                "fg3m":round(float(r["fg3m"]),2)
            })
    payload = {
        "meta":{"season":SEASON,"season_type":SEASON_TYPE,
                "updated_utc":datetime.now(timezone.utc).isoformat(),
                "source":"NBA.com stats via nba_api","rows":len(player_rows),
                "teams":int(logs["TEAM_ABBREVIATION"].nunique()),
                "position_note":"Current roster positions mapped to historical player logs. DvP is average opposing player-game production by broad position group, not official individual matchup tracking."},
        "players":player_rows,"defense":defense
    }
    tmp = OUT + ".tmp"
    with open(tmp,"w",encoding="utf-8") as f:
        json.dump(payload,f,ensure_ascii=False,separators=(",",":"))
    os.replace(tmp,OUT)
    print(f"Wrote {len(player_rows)} player-game rows and {len(defense)} defense-position rows",flush=True)

if __name__ == "__main__":
    main()
