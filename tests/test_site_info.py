"""info(), connect(), server_info and server_caps on the mock (api3 046)."""

KEYS = ["analytics_site_id", "analytics_site_name", "api_max_entities_per_page",
        "authentication_app_session_launcher_enabled", "full_version", "s3_direct_uploads_enabled",
        "s3_enabled_upload_types", "s3_uploads_enabled", "shotgunlocalhost_browser_integration_enabled",
        "unified_login_flow_enabled", "user_authentication_method", "version"]


def test_info_has_the_site_keys(sg):
    info = sg.info()
    assert sorted(info) == KEYS
    assert info["version"] == [8, 91, 0] and len(info["full_version"]) == 4
    assert info["api_max_entities_per_page"] == 5000
    assert info["s3_enabled_upload_types"] == {"*": ["*"]}


def test_connect_server_info_and_caps(sg):
    assert sg.connect() is None
    assert sg.server_info == sg.info()
    assert sg.server_caps.version == (8, 91, 0)
    assert sg.server_caps.is_dev is False


def test_set_info_changes_the_payload(sg):
    sg.set_info(version=[8, 92, 1], api_max_entities_per_page=500)
    assert sg.server_caps.version == (8, 92, 1)
    assert sg.info()["api_max_entities_per_page"] == 500
    sg.info()["version"].append(9)
    assert sg.info()["version"] == [8, 92, 1]


def test_server_info_and_caps_take_an_assigned_value(sg):
    # Upstream mockgun has no server_info or server_caps: callers assign them.
    sg.server_info = {"version": (7, 0, 0)}
    assert sg.server_info == {"version": (7, 0, 0)}
    caps = object()
    sg.server_caps = caps
    assert sg.server_caps is caps
    assert sg.info()["version"] == [8, 91, 0]


def test_deleting_the_assigned_value_restores_the_derived_one(sg):
    sg.server_info = {"version": (7, 0, 0)}
    sg.server_caps = object()
    del sg.server_info
    del sg.server_caps
    assert sg.server_info == sg.info()
    assert sg.server_caps.version == (8, 91, 0)


def test_server_caps_follow_an_assigned_server_info(sg):
    # The client builds both from one info() payload, so they agree.
    sg.server_info = {"version": (7, 0, 0)}
    assert sg.server_caps.version == (7, 0, 0)
    sg.server_caps = object()
    assert sg.server_info == {"version": (7, 0, 0)}


def test_server_info_does_not_read_an_assigned_server_caps(sg):
    sg.server_caps = object()
    assert sg.server_info == sg.info()
