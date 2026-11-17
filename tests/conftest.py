"""Root options and markers for the conformance suite under tests/conformance/."""


def pytest_addoption(parser):
    group = parser.getgroup("conformance")
    group.addoption("--live", action="store_true", default=False,
                    help="Run tests/conformance against the site in .env.local instead of the mock.")
    group.addoption("--live-schema", action="store_true", default=False,
                    help="With --live, also run schema field writes, on fields named sg_zzprobe_mockgun_*.")
    group.addoption("--conformance-out", default=None, metavar="PATH",
                    help="Write each conformance test's markers and outcome to PATH as JSON.")


def pytest_configure(config):
    config.addinivalue_line("markers", 'finding(nnn, api3=None): the sg-groundtruth finding a conformance test rests on; '
                                       'api3 names the api3 record when one exists.')
    config.addinivalue_line("markers", "cell(method, operator, field_type): the coverage table cell a conformance test fills.")
