from .ca import Ca


class CaKia(Ca):
    @property
    def base_url(self) -> str:
        return "kiaconnect.ca"
