# dory-harness

A small assistant harness for a talk-it-out voice or chat companion. Standard library only.

- **Wake-word gating** (`router.addressed`): a name, "hey/okay computer", a short follow-up within 60 s, or a short send-off. Long unaddressed speech is ignored, so it doesn't answer a video playing in the room.
- **Light/hard routing with fallback** (`router.Harness`): light chat goes to a small local model, harder turns (why/how/plan/long/lookups/day recaps) go to a hosted model, a thread stays on the strong brain for 120 s, and each brain falls back to the other. Any two OpenAI-compatible endpoints work (`config.example.json`).
- **Conversation cues** (`conversation.guidance`): short prompt instructions for play, decisions and exploring ideas. No extra model calls.
- **Grounding** (`router.ground`, `trim`): invented biography sentences are dropped, and replies are cut to whole sentences within a spoken length.
- **Fine-tuning log**: every model call is appended to a JSONL file (messages in, raw reply out) for later distillation.
- **Discord log** (`discordlog`): exchanges and file attachments go to a webhook read from `DISCORD_WEBHOOK`, on a background thread that never raises.
- **Daily checklist** (`checklist`): things that must be done by a time, checked by a function you supply, reporting each new miss once per day.

```python
from dory_harness import router, discordlog
h = router.Harness(config, dataset="dataset/calls.jsonl")
d = h.reply("why is the sky blue?", history=[("user", "hi"), ("assistant", "hello")], system="You are a warm, curious friend.")
discordlog.exchange("why is the sky blue?", d["say"], d["brain"], d["route"])
```

Tests: `python3 -m unittest discover -s tests`. These check routing, gating and checklist logic only, not live model quality.
