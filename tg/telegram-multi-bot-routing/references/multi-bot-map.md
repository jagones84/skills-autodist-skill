# Multi-bot map — this machine / Jagones groups

## Bots
- @JagonesBot = Hermes gateway (display "Sabrina"), bot id 8950510851. Token in `~/.hermes/.env`.
- @Jagones_bot = OpenClaw gateway (Raffaella), bot id 7737497525, coordinator agent. Token in `~/.openclaw/gateway.systemd.env`.
- @jagones = Giovanni (owner), Telegram id 407582054. This positive id is the Hermes home_channel and OpenClaw ownerAllowFrom.

## Groups (VERIFY before use — duplicates have existed)
- Current active group title "Group", chat id -5534316691, requireMention=false in OpenClaw (added 2026-09-07). Both bots are admin members.
- Legacy group ids: -5439548994 (old "BOTGROUP"), -1004405755413 — both stale; treat any config entry for them as historical unless re-verified.
- WARNING: message_id counter differences (~7xx vs ~19xxx) and differing invite_links between the two bots are EXPECTED for one physical group — Telegram scopes basic-group message_id sequences and rotates invite links per bot account. They do NOT prove duplicate groups. Trust only the SKILL.md end-to-end probe (send via other bot's token, grep receiving gateway log) for routing truth.
- Legacy group id -1004405755413 appears in old configs; treat any config entry for it as stale unless re-verified.

## Filters (re-verify live, they drift)
- Hermes: `TELEGRAM_ALLOWED_USERS=407582054,7737497525` (Giovanni + Raffaella). `config.yaml` platforms.telegram: `allow_bots: all`, `require_mention: false`. Verified: a probe sent via Raffaella's token appears in Hermes gateway.log as `inbound message: user=Raffaella`.
- OpenClaw openclaw.json: `channels.telegram.groups."*".requireMention=true`, `"-5439548994".requireMention=false`, `groupPolicy=open`, `commands.ownerAllowFrom=[telegram:407582054]`, `richMessages: true`, `streaming.mode=partial`.

## Send a message to an OpenClaw agent from CLI (prior documented invocation)
The openclaw binary is a gateway process wrapper — `cd /tmp` first, then:
`node <openclaw>/dist/index.js agent --agent coordinator -m "..." --json`
Target Telegram DM sessions with `--session-key "agent:coordinator:telegram:direct:407582054"`. Gateway control token `Jagones_`. `/v1/chat/completions` returns 404 (HTTP REST not enabled) — use the CLI, not the REST path.
