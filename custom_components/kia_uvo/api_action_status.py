import time

from .const import ACTION_LOCK_TIMEOUT_IN_SECONDS


class ApiActionStatus:
    xid = None
    _completed = False

    def __init__(self, name: str):
        self.name = name
        self.start_time = time.time()

    def set_xid(self, xid):
        self.xid = xid

    def complete(self):
        self._completed = True

    def completed(self):
        return self._completed

    def expired(self):
        return self.start_time + ACTION_LOCK_TIMEOUT_IN_SECONDS < time.time()
