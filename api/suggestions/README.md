# Suggestion pool

Self-curating starter-question chips for the welcome screen. Each question is
tagged with a `topic` (one of `space`, `animals`, `body`, `nature`, `weather`,
`ocean`, `feelings`, `tech`, `fun`, `art`, `music`, `food`, `history`,
`dinosaurs`, `maths`) so the UI can sample 3 chips from 3 different topics
every time instead of repeating the same theme.

- `pool.json` — baseline pool (~150 warm, curious, age-8 PT-PT questions,
  spread evenly across the topics above). Checked into the repo. Served
  whenever the generated pool is missing or unreadable.
- `generate.py` — reads Diana's memory repo (`about-diana.md` + `memory.md` +
  `people.md` + `recent.md`), asks Claude for ~60 fresh topic-tagged
  questions (~40% personalized to her real current interests, ~60% broad
  variety), then MERGES those with the baseline into one big (~200)
  deduped pool and writes `generated_pool.json`. Never writes a broken/thin
  pool: on any failure (memory repo missing, API error, too few questions
  back) it leaves the existing pool untouched, so `/suggestions` keeps
  serving the last good merge (or the baseline alone, if this has never run
  successfully).
- `generated_pool.json` — the live pool `GET /suggestions` serves first. Not
  checked in (see `.gitignore`) — produced by the cron run.
- `cron.sh` — runs `generate.py` via the API's venv with the repo's `.env`
  loaded, guarded by `flock` against overlapping runs. Not installed
  automatically; see the crontab line below.

## Cron (Pi) — every 6 hours

So the personalized layer evolves through the day rather than sitting fixed
from one daily run:

```
0 */6 * * * /path/to/soft-terminal-llm/api/suggestions/cron.sh >> /path/to/soft-terminal-llm/api/suggestions/cron.log 2>&1
```

Replace `/path/to/soft-terminal-llm` with the repo's actual path on the Pi.
This line is not installed by this session — adding it to crontab is a deploy
step for the orchestrator to run (`crontab -e` on the Pi, or `crontab -l` to
confirm it's there).
