# api3 answers

What a live site answers over api3, recorded by the probes in `probes/`. The corpus in sg-groundtruth is
measured over REST; these files are the api3 side that sg-mockgun reproduces. Code cites one as `# api3 NNN`.
`docs/api3-probe-2026-11-12.md` holds the first answers: schema field writes and the event log.

## Run a probe

Read-only:

```sh
uv run python probes/NNN_slug.py
```

With writes, in the sandbox project only:

```sh
uv run python probes/NNN_slug.py --write
```

Credentials come from `.env.local` here, else `../sg-groundtruth/.env.local`.

## Numbers

| range | topic |
|---|---|
| 001 to 019 | filters |
| 020 to 039 | find options, writes per data type, defaults |
| 040 to 059 | methods beyond CRUD |
| 060 to 079 | server-side behaviour |

## An answer file

`docs/api3/NNN_slug.md`:

```
# NNN slug

re-asks: finding 017, field_types/entity
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/NNN_slug.py

**Q** One question.

| call | answer |
|---|---|
| `find("Shot", [["code", "nope", "x"]])` | Fault `API read() ...` |

**Same as REST:** what matches the corpus entry.
**Differs from REST:** what does not, or "nothing".
**Mock:** what sg-mockgun does, and the test that checks it.
```

Ids, project names, user names and emails become placeholders. API errors, field names and data
types stay as printed.
