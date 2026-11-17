# Changelog

sg-mockgun follows [Semantic Versioning](https://semver.org/). Numbers are pull requests on
[ksallee/sg-mockgun](https://github.com/ksallee/sg-mockgun/pulls).

## 1.0.0

### Filters

- Dotted filters read null on a mismatched link and refuse an unknown path (#30).
- Entity and multi_entity filters answer as a site does (#31).
- Relations per data type answer as a site does (#35).
- Link relations, display names, and refused filters raised before the scan (#42).
- Fault wording, link nulls and relative dates follow api3 answers 001 to 015 (#58).

### find

- `limit`, `page` and `order` apply as a site applies them (#32).
- Page size, `retired_only`, archived projects, `LATEST`, order, link names and retired links follow api3 answers 020 to 027 (#56).

### Writes and records

- Field types are checked on write (#34).
- Defaults, text writes and named entity links (#37).
- Writes per data type follow api3 answers 030 to 039 (#57).
- Create contract, statuses, atomic batch, per-project schema and delete effects follow api3 answers 027 and 060 to 065 (#59).

### Task Templates and scheduling

- Task Templates apply on create and on change. Dates reschedule along dependencies. Task delete and revive follow api3 answers 070 to 074 (#55).
- A template apply lists its Tasks on the entity. Writing a Task's stored `start_date` does not pin it (#65).

### Other methods

- `upload`, thumbnails, `download_attachment`, `get_attachment_download_url` and `share_thumbnail` follow api3 answers 053 to 058 (#53).
- Attention, navigation, site reads and `export_page` follow api3 answers 047 to 052 (#54).
- `summarize`, `text_search` and `info` follow api3 answers 040 to 046 (#60).

### Testing kit

- pytest plugin with the `sg` fixture, JSON seeding, snapshot and restore (#33).
- Conformance suite scaffold and `docs/coverage.md` (#36).
- Conformance cells for each api3 area, a live run on a Flow PT 8.91 site, and the coverage table regenerated from both (#65).
- A mock instance pickles (#40).

### Compatibility

- tk-core's test suite runs against sg-mockgun in CI (#38).
- tk-core's suite passes: `server_info` setters, the `find_one` call shape, naive datetimes as local time (#62).
- Media tests pass on Windows. tk-core setup runs on each Python version (#61).
- CI runs the suite on Python 3.9 to 3.14 on Linux, macOS and Windows (#29).
- `__version__` reads the installed version (#29).

### api3 answers

- Probe harness and answer file format (#41, #48).
- Filters: 001 to 006 (#47), 010 to 014 (#43).
- find options and writes: 020 to 027 (#52), 030 to 039 (#51).
- Methods beyond CRUD: 040 to 046 (#50), 047 to 052 (#45), 053 to 058 (#49).
- Server-side behaviour: 060 to 065 (#44), 070 to 074 (#46).

### Docs and packaging

- Docs site in `site/`, served at sg-mockgun.vercel.app. Changelog, PyPI classifiers, keywords and project URLs, credits. (#63)
- `sg_mockgun.__version__` at package level (#63).

## 0.1.0

- Mockgun vendored from shotgun_api3 3.10.5, with upstream's test suite.
- Bundled Flow PT 8.91 schema, cleaned of site-specific fields (#4).
- `schema_field_create`, `schema_field_update` and `schema_field_delete` write to the schema (#5).
- `EventLogEntry` rows for each write (#6).
- HTTP server for the api3 JSON protocol at `/api3/json` (#8).
- REST field revive next to api3 (#11, #13).
- Autodesk's test schema bundled as `upstream_3_10_5` (#15).
- Publish to PyPI on a GitHub release (#18).
