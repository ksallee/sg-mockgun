# 003 between_arity

re-asks: field_types/number
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, read-only
probe: probes/003_between_arity.py

**Q** What does `between` answer with one, three, zero or a bare value on a number field?

| call on `Version.frame_count` | answer |
|---|---|
| `between [1]` | Fault `API read() 'between' 'relation' expects a 2-element array:\n[1]` |
| `between [1, 100]` | rows |
| `between [1, 50, 100]` | Fault `API read() 'between' 'relation' expects a 2-element array:\n[1, 50, 100]` |
| `between 1` | Fault `... expects a 2-element array:\n[1]` |
| `between []` | Fault `... expects a 2-element array:\n[]` |
| `not_between [1]` | Fault, the 001 shape A refusal for `not_between` |

`\n` is a newline in the message.

**Same as REST:** the wording and the echoed array.
**Differs from REST:** a newline after the colon, where REST has a space.
**Mock:** same wording with a space after the colon, raised as `ShotgunError`. Must change: newline, `Fault`.
