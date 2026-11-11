# NBA Defence Trends

Free static NBA player-prop trend dashboard for the 2026-27 season.

## Features
- Player game logs for PTS, REB, AST, PRA and 3PM
- L5, L10, L15 and season samples
- User-entered sportsbook line and empirical UNDER hit rate
- Opponent production allowed by broad position group (Guards / Forwards / Centers)
- Daily scheduled refresh using GitHub Actions and NBA.com stats through the open-source nba_api package

## Enable GitHub Pages
1. Open **Settings → Pages** in this repository.
2. Under **Build and deployment**, choose **Deploy from a branch**.
3. Select branch **main** and folder **/(root)**, then Save.
4. Dashboard URL: https://nikolastankovic1316-dev.github.io/nba-defence-trends/

## Run data refresh
Open **Actions → Update NBA data → Run workflow**. A scheduled refresh is configured for 08:30 UTC daily.

## Data and limitations
- Source: NBA.com stats endpoints via nba_api; no paid API key is required by the client library.
- NBA.com may rate-limit or block automated requests. A failed run leaves the previous data file untouched.
- Position mapping uses current team rosters, so traded players or role/position changes may be misclassified in historical game logs.
- Defence vs position is average box-score production per opposing player-game against each defending team, grouped into broad roster positions. It is not NBA optical-tracking matchup data.
- No bookmaker lines, injuries, projected minutes or starting-lineup feeds are included. Enter the actual line offered by your bookmaker.
- UNDER hit rate is historical frequency only, not a probability forecast or betting recommendation.

## Local run
```bash
pip install -r requirements.txt
python update_data.py
python -m http.server 8000
```
Then open http://localhost:8000.
