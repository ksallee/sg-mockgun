"""Run tk-core's test suite against sg-mockgun, once with the event log off and once with it on.

Run it with the interpreter to test, from the repo root:

    python tools/run_tk_core.py

It clones tk-core at TK_CORE_COMMIT into ``.tk-core/``, fetches its vendored packages (git LFS) for this
Python, installs tk-toolchain, pytest and this checkout of sg-mockgun with ``--no-deps`` into the
running interpreter, then runs pytest twice. tk-core's licence is not BSD: it is cloned at run time,
never copied into this repo.

Exit status is 0 when both runs pass.
"""

import argparse
import os
import shutil
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET

TK_CORE_REPO = "https://github.com/shotgunsoftware/tk-core.git"
TK_CORE_COMMIT = "07528066274f18f155216519c606a11c375ea88e"
TK_TOOLCHAIN = "git+https://github.com/shotgunsoftware/tk-toolchain.git@4f56979735ff6b4b82ad0d78d7d4ceeb69224e11"
LFS_MEDIA_URL = "https://media.githubusercontent.com/media/shotgunsoftware/tk-core/{commit}/{path}"

# authentication_tests and integration_tests need a live site. tests/python is the test framework,
# and its sgtk_integration_test.py matches pytest's file pattern.
IGNORED = ("tests/authentication_tests", "tests/integration_tests", "tests/python")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHIM_DIR = os.path.join(ROOT, "tests", "tk_core")


def run(cmd, **kwargs):
    """Echo and run a command, raising on a non-zero exit."""
    print("+ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kwargs)


def clone(workdir):
    """Clone tk-core at the pinned commit, without LFS content."""
    if os.path.isdir(os.path.join(workdir, ".git")):
        run(["git", "-C", workdir, "checkout", "-q", TK_CORE_COMMIT])
        return
    os.makedirs(workdir, exist_ok=True)
    env = dict(os.environ, GIT_LFS_SKIP_SMUDGE="1")
    run(["git", "-C", workdir, "init", "-q"], env=env)
    run(["git", "-C", workdir, "fetch", "-q", "--depth", "1", TK_CORE_REPO, TK_CORE_COMMIT], env=env)
    run(["git", "-C", workdir, "checkout", "-q", "FETCH_HEAD"], env=env)


def fetch_vendored_packages(workdir):
    """Fetch requirements/<py>/pkgs.zip and requirements/any/*.zip, with git lfs when installed, else over HTTPS."""
    version_dir = "requirements/%d.%d" % sys.version_info[:2]
    if not os.path.isdir(os.path.join(workdir, version_dir)):
        raise SystemExit("tk-core has no %s. It supports Python 3.9, 3.10, 3.11 and 3.13." % version_dir)
    paths = [version_dir + "/pkgs.zip"]
    paths += sorted("requirements/any/" + name for name in os.listdir(os.path.join(workdir, "requirements", "any"))
                    if name.endswith(".zip"))
    for path in paths:
        target = os.path.join(workdir, path)
        with open(target, "rb") as fh:
            if fh.read(2) == b"PK":
                continue
        if shutil.which("git-lfs"):
            run(["git", "-C", workdir, "lfs", "pull", "--include", path])
            continue
        url = LFS_MEDIA_URL.format(commit=TK_CORE_COMMIT, path=path)
        print("+ download " + url, flush=True)
        with urllib.request.urlopen(url) as response, open(target, "wb") as out:
            shutil.copyfileobj(response, out)


def install():
    """Install the test tools and sg-mockgun into the running interpreter."""
    pip = [sys.executable, "-m", "pip", "install", "-q"]
    # tk-toolchain's own dependencies are PySide and Sphinx, for its doc tools. Its pytest plugin
    # needs pytest and ruamel.yaml.
    run(pip + ["pytest", "ruamel.yaml"])
    run(pip + ["--no-deps", TK_TOOLCHAIN])
    # tk-core's shotgun_api3 comes from pkgs.zip. A second copy would give sg_mockgun another Fault.
    run(pip + ["--no-deps", "--force-reinstall", ROOT])


def run_suite(workdir, label, event_log, extra):
    """Run tk-core's suite once and return (exit code, counts)."""
    junit = os.path.join(workdir, "results-%s.xml" % label)
    env = dict(os.environ)
    env["SG_MOCKGUN_EVENT_LOG"] = "1" if event_log else "0"
    env["PYTHONPATH"] = os.pathsep.join(p for p in (SHIM_DIR, env.get("PYTHONPATH")) if p)
    # sg_mockgun's own pytest11 plugin imports shotgun_api3 before tank_vendor has put tk-core's
    # copy on sys.path, so it is turned off. The shim imports sg_mockgun after tank_vendor.
    cmd = [sys.executable, "-m", "pytest", "-p", "no:sg_mockgun", "-p", "sg_mockgun_tk_core_shim", "tests",
           "-q", "-rfE", "--tb=short", "-p", "no:cacheprovider", "--junitxml", junit]
    cmd += ["--ignore=%s" % path for path in IGNORED]
    cmd += extra
    print("\n=== tk-core, event log %s ===" % ("on" if event_log else "off"), flush=True)
    print("+ " + " ".join(cmd), flush=True)
    code = subprocess.run(cmd, cwd=workdir, env=env).returncode
    return code, junit_counts(junit)


def junit_counts(path):
    """Return tests, failures, errors and skipped from a JUnit XML file."""
    if not os.path.exists(path):
        return {}
    root = ET.parse(path).getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    return {key: int(suite.get(key, 0)) for key in ("tests", "failures", "errors", "skipped")}


def main():
    """Parse arguments, prepare tk-core and run both passes."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workdir", default=os.path.join(ROOT, ".tk-core"), help="tk-core checkout.")
    parser.add_argument("--skip-install", action="store_true", help="Reuse the installed packages.")
    parser.add_argument("pytest_args", nargs="*", help="Passed to pytest, after --.")
    args = parser.parse_args()

    workdir = os.path.abspath(args.workdir)
    clone(workdir)
    fetch_vendored_packages(workdir)
    if not args.skip_install:
        install()

    results = []
    for label, event_log in (("event-log-off", False), ("event-log-on", True)):
        code, counts = run_suite(workdir, label, event_log, args.pytest_args)
        results.append((label, code, counts))

    print("\n=== summary ===")
    for label, code, counts in results:
        print("%s: exit %d, %s" % (label, code, counts))
    return 0 if all(code == 0 for _, code, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
