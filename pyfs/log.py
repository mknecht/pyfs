from functools import wraps
import logging
import traceback


def logcall(f):
    log = logging.getLogger(f.__name__)

    def getattrs(o):
        collected = []
        for name in dir(o):
            if name.startswith("logme_"):
                collected.append("{}={}".format(name[6:], getattr(o, name)))
        return "{}({})".format(o.__class__.__name__, ", ".join(collected))

    @wraps(f)
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
