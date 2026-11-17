"""api3 046: the payload of info(), and what connect(), server_info and server_caps do with it."""
import _lib
import shotgun_api3


def shape(value):
    """The value with strings replaced by their type name: booleans and numbers are not site data."""
    if isinstance(value, dict):
        return {k: shape(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return [shape(v) for v in value]
    if isinstance(value, str):
        return "<str>"
    return value


def main():
    env = _lib.load_env()
    sg = _lib.client(env)
    info = sg.info()
    answers = {
        "info": shape(info),
        "user_authentication_method": info.get("user_authentication_method"),
        "s3_enabled_upload_types": info.get("s3_enabled_upload_types"),
        "server_caps_version_type": type(sg.server_caps.version).__name__,
        "connect_returns": _lib.ask(sg.connect),
        "server_info_is_info": sg.server_info == info,
        "server_caps_version": sg.server_caps.version,
        "server_caps_is_dev": sg.server_caps.is_dev,
    }
    # info() takes no auth: a client with a wrong key still gets the payload.
    bad = shotgun_api3.Shotgun(_lib.need(env, "FPT_API_SITE_URL"), script_name="zzprobe_not_a_script",
                               api_key="not-a-key", connect=False)
    answers["info_with_bad_key"] = _lib.ask(lambda: sorted(bad.info()) == sorted(info))
    answers["connect_with_bad_key"] = _lib.ask(bad.connect)
    answers["find_one_with_bad_key"] = _lib.ask(bad.find_one, "Project", [])
    _lib.emit("046_info", answers, env, sg)


if __name__ == "__main__":
    main()
