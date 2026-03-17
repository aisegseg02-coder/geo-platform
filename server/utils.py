import time
import functools

def retry(backoff_base=1.0, attempts=3, exceptions=(Exception,)):
    """Decorator to retry a function with exponential backoff.

    Usage:
      @retry(attempts=3)
      def foo(...):
          ...
    """
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*a, **kw):
            last = None
            for i in range(attempts):
                try:
                    return fn(*a, **kw)
                except exceptions as e:
                    last = e
                    delay = backoff_base * (2 ** i)
                    time.sleep(delay)
            raise last
        return wrapper
    return deco
