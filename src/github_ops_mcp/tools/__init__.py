import functools
import subprocess


def ok(data):
    return {"ok": True, "data": data, "error": None}


def fail(msg: str):
    return {"ok": False, "data": None, "error": str(msg)}


def safe_call(fn):
    """Wrap a tool in the standard envelope, preserving the real signature
    so FastMCP can introspect parameter names."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return ok(fn(*args, **kwargs))
        except PermissionError as e:
            return fail(f"blocked: {e}")
        except ValueError as e:
            return fail(str(e))
        except FileNotFoundError as e:
            return fail(f"not found: {e}")
        except subprocess.TimeoutExpired:
            return fail("command timed out")
        except Exception as e:
            return fail(f"{type(e).__name__}: {e}")
    return wrapper
