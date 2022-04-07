"""Luci API client exceptions."""


class LuciException(BaseException):
    pass


class LuciConnectionException(LuciException):
    pass


class LuciTokenException(LuciException):
    pass
