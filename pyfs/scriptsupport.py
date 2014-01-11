import json
import sys


def run_with(what, funcargs):
    res = what(*funcargs)
    if res is True:
        return 0
    if res is False:
        return 4
    if res is not None:
        print(encode_output(res))
        return None


def decode_input(s):
    try:
        return json.loads(s)
    except ValueError:
        return s


def encode_output(obj):
    if isinstance(obj, basestring):
        return obj
    try:
        return json.dumps(obj)
    except TypeError:
        return repr(obj)


def decode_strings(encoded):
    return [decode_input(el) for el in encoded]


def run_for_input(what, args):
    if not sys.stdin.isatty():
        stdin_idx = args.index("-") if "-" in args else None
        for line in get_line_from_stdin():
            element = decode_input(line)
            funcargs = decode_strings(args)
            if stdin_idx is not None:
                funcargs[stdin_idx:stdin_idx+1] = [element]
            else:
                funcargs[0:0] = [element]
            return run_with(what, funcargs)
    else:
        return run_with(what, decode_strings(args))


def exit_with(value):
    sys.exit(value if isinstance(value, int) else 0)


def get_line_from_stdin():
    buff = ''
    while True:
        ch = sys.stdin.read(1)
        if len(ch) == 0:  # end of file
            break
        if ch != "\n":
            buff += ch
        else:
            yield buff
            buff = ''
