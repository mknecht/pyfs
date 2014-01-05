#!/usr/bin/env python
#
# Implementation of a filesystem that will show a file and a directory
# when executing ls on the root.
#
# Copyright (c) 2014 Murat Knecht
# License: MIT
#

from __future__ import print_function
from __future__ import absolute_import

import errno
from itertools import chain, count
import os
import logging
import stat
import sys

import fuse

from pyfs.common import (
    add_module,
    is_dir,
    is_executable,
    is_file,
    get_content,
    get_elements,
    logcall,
    PATH_MODULES,
    read_from_string,
    reset_modules_list,
)


class PyFS(fuse.Operations):

    def __init__(self):
        super(PyFS, self).__init__()
        self._next_fh = count()
        self._flags_for_open_files = {}  # file handle -> fh
        for name in ("json", "os", "sys"):
            add_module(name)
        self._log = logging.getLogger(self.__class__.__name__)

    @logcall
    def getattr(self, path, fh=None):
        if path == '/' or path == "/." or path == "/..":
            return dict(
                st_mode=stat.S_IFDIR | 0555,
                st_nlink=2,
            )
        elif is_dir(path):
            return dict(
                st_mode=stat.S_IFDIR | 0555,
                st_nlink=3,
            )
        elif is_file(path):
            def _get_file_mode():
                if is_executable(path):
                    return 0555
                elif path == PATH_MODULES:
                    return 0666
                else:
                    return 0444
            return dict(
                st_mode=stat.S_IFREG | _get_file_mode(),
                st_nlink=1,
                st_size=len(get_content(path)),
            )
        else:
            raise fuse.FuseOSError(errno.ENOENT)

    @logcall
    def read(self, path, size, offset, fh):
        return read_from_string(
            get_content(path),
            size,
            offset,
        )

    @logcall
    def readdir(self, path, fh):
        return [name for name in chain([".", ".."], get_elements(path))]

    def open(self, path, flags):
        if path == PATH_MODULES:
            if flags & os.O_RDWR:
                self._log.debug(
                    "Cannot allow readwrite access. Flags: {}".format(flags))
                raise fuse.FuseOSError(errno.EPERM)
            if flags & os.O_TRUNC:
                reset_modules_list()
        else:
            if flags & os.O_WRONLY or flags & os.O_RDWR:
                self._log.debug(
                    "Cannot write to Python objects. Flags: {}".format(flags))
                raise fuse.FuseOSError(errno.EPERM)

        fh = self._next_fh.next()
        self._flags_for_open_files[fh] = flags
        return fh

    def truncate(self, path, length, fh=None):
        if path != PATH_MODULES:
            raise fuse.FuseOSError(errno.EPERM)
        if length != 0:
            self._log.debug("Must completely truncate the modules file.")
            raise IOError(errno.EPERM)
        reset_modules_list()

    def release(self, path, fh):
        if fh not in self._flags_for_open_files:
            # EBADFD = "File descriptor in bad state" (not sure it's correct)
            raise fuse.FuseOSError(errno.EBADFD)
        del self._flags_for_open_files[fh]
        return fh

    def write(self, path, data, offset, fh):
        if fh not in self._flags_for_open_files:
            # EBADFD = "File descriptor in bad state" (not sure it's correct)
            raise fuse.FuseOSError(errno.EBADFD)
        if not self._flags_for_open_files[fh] & os.O_APPEND and offset != 0:
            self._log.debug("Must either append to or truncate a file.")
            raise fuse.FuseOSError(-errno.EPERM)
        if data.strip():
            add_module(data.strip())
        return len(data)


if __name__ == '__main__':
    logging.basicConfig(filename="pyfs.log", filemode="w")
    logging.getLogger().setLevel(logging.DEBUG)
    fuse.FUSE(PyFS(), sys.argv[1])
