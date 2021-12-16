import logging

_LOGGER = logging.getLogger(__name__)


class CallbacksMixin:
    def _setup_callbacks(self):
        self._callbacks = set()

    def register_callback(self, callback) -> None:
        if not hasattr(self, "_callbacks"):
            self._setup_callbacks()
        self._callbacks.add(callback)

    def remove_callback(self, callback) -> None:
        if not hasattr(self, "_callbacks"):
            self._setup_callbacks()
        self._callbacks.discard(callback)

    def publish_updates(self) -> None:
        if not hasattr(self, "_callbacks"):
            self._setup_callbacks()
        for callback in self._callbacks:
            callback()
