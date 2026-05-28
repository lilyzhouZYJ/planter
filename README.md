# 🌱 planter

a tiny terminal app for growing your ideas into done things.

organize tasks by feature, track progress, and leave notes along the way — all from the comfort of your terminal.

---

## getting started

```bash
pip install -r requirements.txt
python planter.py
```

## layout

```
┌─ Features ──┬─── Tasks ──────────────┬─── History ───────────┐
│             │                        │                        │
│  auth  (2)  │   ✦ todo  login page   │  [Note] looks good    │
│  backend(5) │   ✦ done  signup flow  │  [Status] todo → done │
│  misc  (1)  │                        │                        │
└─────────────┴────────────────────────┴────────────────────────┘
```

## keybindings

| key | action |
|-----|--------|
| `f` | new feature |
| `n` | new task |
| `s` | set task status |
| `a` | add history entry |
| `r` | rename task |
| `R` | rename feature |
| `d` | delete |
| `q` | quit |

## task statuses

`todo` · `in-progress` · `done` · `blocked`

## history entry types

`Note` · `Status` · `Blocker` · `Update`

---

data lives in `~/.planter/data.json`.
