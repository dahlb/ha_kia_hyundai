from aiohttp import ClientError


class AuthError(ClientError):
    pass
