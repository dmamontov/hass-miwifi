"""Luci API client exceptions."""


class LuciException(BaseException):
    """Luci error"""


class LuciConnectionException(LuciException):
    """Luci connection error"""


class LuciTokenException(LuciException):
    """Luci token error"""
