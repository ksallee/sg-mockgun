"""Pull a clean schema from a live site, pickled for mockgun.

    uv run python tools/pull_schema.py --env path/to/.env --out src/sg_mockgun/schemas/<name>

Read-only: schema_read and schema_entity_read. The env file holds FPT_API_SITE_URL,
FPT_API_SCRIPT_NAME and FPT_API_API_KEY; nothing from it is printed or written.
"""

import argparse
import json
import pathlib
import pickle

from shotgun_api3 import Shotgun

from sg_mockgun.clean import clean_schema

ROOT = pathlib.Path(__file__).resolve().parents[1]


def read_env(path):
    env = {}
    for line in pathlib.Path(path).read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip("'\"")
    return env


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--env", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--report", help="write what was dropped here; it names the site's own fields, keep it out of the repo")
    parser.add_argument("--upstream", default=str(ROOT / "tests" / "fixtures" / "upstream" / "schema.pickle"))
    args = parser.parse_args()

    env = read_env(args.env)
    sg = Shotgun(env["FPT_API_SITE_URL"], script_name=env["FPT_API_SCRIPT_NAME"], api_key=env["FPT_API_API_KEY"])
    version = ".".join(str(n) for n in sg.server_info.get("version", [])[:3])
    upstream = pickle.loads(pathlib.Path(args.upstream).read_bytes())

    schema, entities, report = clean_schema(sg.schema_read(), sg.schema_entity_read(), upstream)

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "schema.pickle").write_bytes(pickle.dumps(schema, protocol=2))
    (out / "schema_entity.pickle").write_bytes(pickle.dumps(entities, protocol=2))
    report["server_version"] = version
    report["entities"] = len(schema)
    report["fields"] = sum(len(f) for f in schema.values())
    if args.report:
        pathlib.Path(args.report).write_text(json.dumps(report, indent=1) + "\n")
    print(f"{report['entities']} entities, {report['fields']} fields, server {version}")


if __name__ == "__main__":
    main()
