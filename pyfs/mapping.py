from __future__ import absolute_import
import errno
import importlib
import logging
import os
import traceback
import types

from pyfs.log import logcall


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

DIR_BIN = "bin"
DIR_DOT = "dot"
DIR_LIB = "lib"
DIR_MODULES = "modules"
DIR_RUN = "run"

PATH_BIN_PREFIX = "/{}/".format(DIR_BIN)
PATH_DOT_PREFIX = "/{}/".format(DIR_DOT)
PATH_LIB_PREFIX = "/{}/".format(DIR_LIB)
PATH_MODULES = "/{}/{}".format(DIR_RUN, DIR_MODULES)

root_namespace = {
    DIR_BIN: {},
    DIR_DOT: {},
    DIR_RUN: {DIR_MODULES: None},
    DIR_LIB: {},
}


class CannotResolve(RuntimeError):
    def __init__(self, qname):
        super(CannotResolve, self).__init__("Cannot resolve ".format(qname))
        self.what = " ".join(qname)


class SymLink(object):
    def __init__(self, targetpath):
        super(SymLink, self).__init__()
        self._targetpath = targetpath

    @property
    def content(self):
        return self._targetpath


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


def is_symlink(path):
    return isinstance(_resolve(_path_to_qname(path)), SymLink)


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
            if (
                    is_file(child_path) or
                    is_dir(child_path) or
                    is_symlink(child_path)
            ):
                chosen_names.append(name)
    log.debug("For {} got contents: {}".format(path, chosen_names))
    return chosen_names


def add_module(name):
    try:
        root_namespace[DIR_LIB][name] = importlib.import_module(name)
    except ImportError:
        log.debug(traceback.format_exc())
        raise IOError(-errno.ENXIO)


def add_symlink(sourcepath, targetpath):
    source = _path_to_qname(sourcepath)
    _resolve(source[:-1])[source[-1]] = SymLink(targetpath)


def reset_modules_list():
    root_namespace[DIR_LIB] = {}


@logcall
def get_content(path, path_to_projectdir):
    if path == PATH_MODULES:
        return "\n".join(_get_modules())
    elif path.startswith(PATH_DOT_PREFIX):
        return _render_template(
            DIR_DOT, path_to_projectdir, attr_name=path[len(PATH_DOT_PREFIX):])
    else:
        return _get_content_for_path(path, path_to_projectdir)


def _get_modules():
    return root_namespace[DIR_LIB].keys()


def _path_to_qname(path):
    return [n for n in path.split("/") if n]


def _render_template(filename, path_to_projectdir, **kwargs):
    assignments = dict(**kwargs)
    assignments["pyfs_module_path"] = path_to_projectdir
    log.warn(os.getcwd())
    with open(
            os.path.abspath(
                os.path.join(
                    path_to_projectdir,
                    "templates",
                    filename,
                )
            )
            ) as f:
        return f.read().format(**assignments)


@logcall
def _get_content_for_path(path, path_to_projectdir):
    qname = _path_to_qname(path)
    obj = _resolve(qname)
    if is_executable(path):
        return _render_template(
            "call_thing",
            path_to_projectdir,
            modulename=".".join(qname[1:-1]),
            thingname=qname[-1],
        )
    elif isinstance(obj, SymLink):
        return obj.content
    elif _is_datafile(path):
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
            if name not in root_namespace:
                raise CannotResolve(qname)
            obj = root_namespace[name]
        elif len(qname) - len(parts) == 2:
            if name not in obj:
                raise CannotResolve(qname)
            obj = obj[name]
        else:
            pyname = name[1:] if name.startswith(".") else name
            try:
                obj = getattr(obj, pyname)
            except AttributeError:
                raise CannotResolve(qname)
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
