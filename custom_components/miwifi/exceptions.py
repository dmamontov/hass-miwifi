"""Luci API client exceptions."""


class LuciError(BaseException):
    """Luci error"""


class LuciConnectionError(LuciError):
    """Luci connection error"""


class LuciRequestError(LuciError):
    """Luci request error"""
