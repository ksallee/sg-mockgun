"""`between` with one, two and three values on a number field."""
import _lib


def main():
    env = _lib.load_env()
    sg = _lib.client(env)
    answers = {}
    for values in ([1], [1, 100], [1, 50, 100], 1, []):
        answers["between %r" % (values,)] = _lib.ask(
            sg.find, "Version", [["frame_count", "between", values]], ["id"], limit=1)
    for values in ([1], [1, 50, 100]):
        answers["not_between %r" % (values,)] = _lib.ask(
            sg.find, "Version", [["frame_count", "not_between", values]], ["id"], limit=1)
    _lib.emit("003_between_arity", answers, env, sg)


if __name__ == "__main__":
    main()
