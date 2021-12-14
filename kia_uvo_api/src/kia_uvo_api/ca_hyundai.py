from .ca import Ca


class CaHyundai(Ca):
    @property
    def base_url(self) -> str:
        return "www.mybluelink.ca"
