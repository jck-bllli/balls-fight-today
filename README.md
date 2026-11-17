# Balls Fight Today

Daily ball race Reels for [@ballsfighttoday](https://www.instagram.com/ballsfighttoday/), posted through the official Instagram API.

Two gravity balls bounce in their own boxes. Every floor hit damages the HP bar under the ball; bars break one at a
time and the ball falls to the next. Damage grows by each ball's rule (Fibonacci, doubling, steady, counting, growing,
splitting...). Each race is a real simulation, searched so the finish is a split-second comeback, a photo finish, or a
1 to 3 s loss (rotation in `ballsim.MIX`). All art is original.

- `generator/ballsim.py` sim, near-tie search and render. `generator/daily.py` picks a fresh matchup, renders, queues it.
- `generator/state.json` matchup history and pairs that never tie
- `queue.json` / `posted.json` posting order and history (`style` = the pair, `mode` = result type; Otto reads `style`)
- `.github/workflows/render.yml` daily on the home PC (label `render-pc`), keeps 4 races ready. Test: Run workflow with test ticked.
  `post.yml` posts daily at 17:17 UTC (9:17am PT) with a 90 min backup. `otto.yml` ranks matchups every Monday.
- New ball type: add it to `RULES` in ballsim.py, run `python generator/daily.py --survey` to see which pairs tie.

## Secrets (repo Settings > Secrets and variables > Actions)
`IG_ACCESS_TOKEN` (Instagram login token for @ballsfighttoday), `GH_PAT` (fine-grained, this repo, Secrets read/write, lets the
workflow save the renewed token), `FB_ACCESS_TOKEN` (Otto competitor research, optional).

## Home PC
Runner `home-pc` (label `render-pc`) is installed as a service in C:\\runners\\ballsfight.
