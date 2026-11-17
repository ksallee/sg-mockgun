# sg-mockgun

sg-mockgun replaces `shotgun_api3.lib.mockgun` with an in-memory Flow Production Tracking mock that
answers as a live site answers over api3.

## Install

```sh
pip install sg-mockgun
```

Requires Python 3.9 or later and `shotgun-api3` 3.10.5 or later.

## Quick start

```python
from sg_mockgun import Shotgun, schemas

Shotgun.set_schema_paths(*schemas.paths())
sg = Shotgun("https://mock.example.com", script_name="x", api_key="y")
sg.create("Project", {"name": "Demo"})
```

## Docs

The site is [sg-mockgun.vercel.app](https://sg-mockgun.vercel.app). Its source is `site/`.

- [Install and migrate from shotgun_api3's mockgun](https://sg-mockgun.vercel.app/docs/migrate/)
- [Testing with pytest](https://sg-mockgun.vercel.app/docs/pytest/)
- [HTTP server](https://sg-mockgun.vercel.app/docs/server/)
- [What is modelled](https://sg-mockgun.vercel.app/docs/modelled/)
- [Coverage](https://github.com/ksallee/sg-mockgun/blob/main/docs/coverage.md): each api3 call the conformance suite checks.
- [api3 answers](https://github.com/ksallee/sg-mockgun/blob/main/docs/api3/README.md): what a live site answered, per probe.
- [Changelog](https://github.com/ksallee/sg-mockgun/blob/main/CHANGELOG.md)

## Develop

```sh
uv sync
uv run pytest
```

## Credits

Behaviour in sg-mockgun was measured on a live site, not copied. These upstream changes cover the
same ground:

- Patrick Wolf, [python-api#466](https://github.com/shotgunsoftware/python-api/pull/466): currency, timecode, uuid, color, password, image and jsonb fields.
- Patrick Wolf, [python-api#467](https://github.com/shotgunsoftware/python-api/pull/467): default values in the types the server returns.
- Patrick Wolf, [python-api#468](https://github.com/shotgunsoftware/python-api/pull/468): `limit` and `page` in `find`.
- Patrick Wolf, [python-api#469](https://github.com/shotgunsoftware/python-api/pull/469): `upload`.
- Patrick Wolf, [python-api#470](https://github.com/shotgunsoftware/python-api/pull/470): `download_attachment`.
- Alex Hughes, [python-api#197](https://github.com/shotgunsoftware/python-api/pull/197): loading data from a production site.
- Kevin Sallee, [tk-core#963](https://github.com/shotgunsoftware/tk-core/pull/963): mockgun filter comparison fixes.

## License

BSD-3-Clause, as upstream. `src/sg_mockgun/` started as `shotgun_api3/lib/mockgun` from
shotgun_api3 3.10.5, Copyright (c) 2009-2011 Shotgun Software Inc. `tests/test_upstream_mockgun.py`
and `tests/fixtures/upstream/` are upstream's tests and test schema, with import paths changed.
