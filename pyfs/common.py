import errno
import importlib
import logging
import os
import traceback
import types


log = logging.getLogger(__name__)

VALUE_TYPES = [
    types.BooleanType,
    types.ComplexType,
    types.DictProxyType,
    types.DictType,
    types.DictionaryType,
    types.FileType,
    types.FloatType,
    types.IntType,
    types.ListType,
    types.LongType,
    types.NoneType,
    types.StringType,
    types.StringTypes,
    types.TracebackType,
    types.TupleType,
]

__EXEC_TEMPLATE = """#!/usr/bin/python

import sys
import {modulename}

if __name__ == '__main__':
    print({modulename}.{functionname}(*sys.argv[1:]))

"""

PATH_MODULES = "/run/modules"

root_namespace = {
    "run": {"modules": None},
    "lib": {},
}


def logcall(f):
    log = logging.getLogger(f.__name__)

    def getattrs(o):
        collected = []
        for name in dir(o):
            if name.startswith("logme_"):
                collected.append("{}={}".format(name[6:], getattr(o, name)))
        return "{}({})".format(o.__class__.__name__, ", ".join(collected))

    def logged(*args, **kw):
        log.debug("Calling {}(*{}, **{}) on {}".format(
            f.__name__, args, kw, None if not args else getattrs(args[0])))
        try:
            ret = f(*args, **kw)
        except Exception:
            log.debug(
                "Called: {}(*{}, **{}) on {} and got exception {}".format(
                    f.__name__,
                    args,
                    kw,
                    None if not args else getattrs(args[0]),
                    traceback.format_exc(),
                )
            )
            raise
        log.debug("Called: {}(*{}, **{}) on {} -> {}".format(
            f.__name__, args, kw, None if not args else getattrs(args[0]), ret
        ))
        return ret
    return logged


def is_dir(path):
    return (
        path[1:] in root_namespace or
        isinstance(_resolve(_path_to_qname(path)), types.ModuleType)
    )


def is_file(path):
    return (
        is_executable(path) or
        _is_datafile(path)
    )


def is_executable(path):
    return (
        hasattr(_resolve(_path_to_qname(path)), "__call__")
    )


@logcall
def get_elements(path):
    log.debug("Getting contents for: {}".format(path))
    qname = _path_to_qname(path)

    def _get_visible_elements():
        if qname == []:
            return root_namespace.keys()
        if len(qname) == 1:
            return root_namespace[path[1:]].keys()
        else:
            return dir(_resolve(qname))

    all_names = []
    for name in _get_visible_elements():
        all_names.append(
            "{prefix}{name}".format(
                prefix=(
                    "."
                    if name.startswith("_")
                    and not (name.startswith("__") and name.endswith("__"))
                    else ""),
                name=name,
            )
        )
    log.debug("Got unfiltered elements for path {}: {}".format(
        path, all_names))

    chosen_names = []
    for name in all_names:
        if len(qname) == 0:
            chosen_names.append(name)
        else:
            child_path = "/" + "/".join(qname + [name])
            if is_file(child_path) or is_dir(child_path):
                chosen_names.append(name)
    log.debug("For {} got contents: {}".format(path, chosen_names))
    return chosen_names


def add_module(name):
    try:
        root_namespace["lib"][name] = importlib.import_module(name)
    except ImportError:
        log.debug(traceback.format_exc())
        raise IOError(-errno.ENXIO)


def reset_modules_list():
    root_namespace["lib"] = {}


@logcall
def get_content(path):
    if path == PATH_MODULES:
        return "\n".join(_get_modules())
    else:
        return _render_template(path)


def _get_modules():
    return root_namespace["lib"].keys()


def _path_to_qname(path):
    return [n for n in path.split("/") if n]


@logcall
def _render_template(path):
    qname = _path_to_qname(path)
    if is_executable(path):
        return __EXEC_TEMPLATE.format(
            modulename=".".join(qname[1:-1]),
            functionname=qname[-1],
        )
    elif _is_datafile(path):
        obj = _resolve(qname)
        if isinstance(obj, list):
            return os.linesep.join(obj)
        return str(obj)
    else:
        raise IOError("Cannot read unknown filetype", errno.ENOTSUP)


def _resolve(qname):
    log.debug("Resolving: {}".format(qname))
    obj = None
    parts = qname[:]
    while parts:
        name = parts.pop(0)
        if obj is None:
            obj = root_namespace[name]
        elif len(qname) - len(parts) == 2:
            obj = obj[name]
        else:
            pyname = name[1:] if name.startswith(".") else name
            obj = getattr(obj, pyname)
    log.debug("Resolved {} to {})".format(qname, obj))
    return obj


def _is_datafile(path):
    return (
        path == PATH_MODULES or
        any(
            isinstance(_resolve(_path_to_qname(path)), type_)
            for type_ in VALUE_TYPES
        )
    )


def read_from_string(text, size, offset):
        slen = len(text)
        if offset < slen:
            if offset + size > slen:
                size = slen - offset
            buf = text[offset:offset+size]
        else:
            buf = ''
        return buf
