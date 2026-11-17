# Balls Fight Today

Daily ball race Reels for [@ballsfighttoday](https://www.instagram.com/ballsfighttoday/), posted through the official Instagram API.

Two balls bounce in their own lanes. Each wall hit damages 3 HP layers, and damage grows by the ball's own rule
(Fibonacci, doubling, cube, steady, and so on). First to break all layers wins. Comeback modes (`none`, `catchup`,
`second_wind`) help the trailing ball. All art is original.

- `generator/engine.py` race simulation, `render.py` 1080x1920 video, `plan.py` picks matchups, `produce.py` renders and queues
- `generator/matchups.json` planned matchups (id, balls, comeback mode, visual style, caption)
- `queue.json` / `posted.json` posting order and history (`style` and `mode` tags feed Otto)
- `.github/workflows/plan.yml` Sundays: plans 14 matchups. `render.yml` renders new ones on the home PC (label `render-pc`).
  `post.yml` posts daily at 17:17 UTC (9:17am PT) with a 90 min backup. `otto.yml` ranks our styles every Monday.

## Secrets (repo Settings > Secrets and variables > Actions)
`IG_ACCESS_TOKEN` (Instagram login token for @ballsfighttoday), `GH_PAT` (fine-grained, this repo, Secrets read/write, lets the
workflow save the renewed token), `FB_ACCESS_TOKEN` (Otto competitor research, optional).

## Home PC
Register a self-hosted runner for this repo with label `render-pc` (same as the other repos). Test render: Actions > Render on home PC > Run workflow > test.
