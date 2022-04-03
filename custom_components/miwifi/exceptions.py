"""Luci API client exceptions."""

class LuciException(Exception):
    pass

class LuciConnectionException(LuciException):
    pass

class LuciTokenException(LuciException):
    pass
