"""Enums."""

from __future__ import annotations

from enum import IntEnum, Enum

from .const import (
    ATTR_SWITCH_WIFI_2_4,
    ATTR_SWITCH_WIFI_5_0,
    ATTR_SWITCH_WIFI_5_0_GAME,
)


class Mode(IntEnum):
    """Mode enum"""

    def __new__(cls, value: int, phrase: str = "undefined") -> "Mode":
        """New mode.

        :param value: int: mode
        :param phrase: str: phrase
        :return Mode
        """

        obj = int.__new__(cls, value)  # type: ignore
        obj._value_ = value

        obj.phrase = phrase  # type: ignore

        return obj

    def __str__(self) -> str:
        """Serialize to string.

        :return str
        """

        return str(self.value)

    DEFAULT = 0, "default"
    REPEATER = 1, "repeater"
    ACCESS_POINT = 2, "access_point"
    MESH = 9, "mesh"


class Connection(IntEnum):
    """Connection enum"""

    def __new__(cls, value: int, phrase: str = "undefined") -> "Connection":
        """New connection.

        :param value: int: mode
        :param phrase: str: phrase
        :return Connection
        """

        obj = int.__new__(cls, value)  # type: ignore
        obj._value_ = value

        obj.phrase = phrase  # type: ignore

        return obj

    def __str__(self) -> str:
        """Serialize to string.

        :return str
        """

        return str(self.value)

    LAN = 0, "Lan"
    WIFI_2_4 = 1, "2.4G"
    WIFI_5_0 = 2, "5G"
    GUEST = 3, "Guest"
    WIFI_5_0_GAME = 6, "5G Game"


class IfName(str, Enum):
    """IfName enum"""

    def __new__(cls, value: str, phrase: str = "undefined") -> "IfName":
        """New ifname.

        :param value: str: ifname
        :param phrase: str: phrase
        :return IfName
        """

        obj = str.__new__(cls, value)  # type: ignore
        obj._value_ = value

        obj.phrase = phrase  # type: ignore

        return obj

    def __str__(self) -> str:
        """Serialize to string.

        :return str
        """

        return str(self.value)

    WL0 = "wl0", ATTR_SWITCH_WIFI_5_0
    WL1 = "wl1", ATTR_SWITCH_WIFI_2_4
    WL2 = "wl2", ATTR_SWITCH_WIFI_5_0_GAME


class Wifi(IntEnum):
    """Wifi enum"""

    def __new__(cls, value: int, phrase: str = "undefined") -> "Wifi":
        """New Wifi.

        :param value: int: WifiIndex
        :param phrase: str: phrase
        :return Wifi
        """

        obj = int.__new__(cls, value)  # type: ignore
        obj._value_ = value

        obj.phrase = phrase  # type: ignore

        return obj

    def __str__(self) -> str:
        """Serialize to string.

        :return str
        """

        return str(self.value)

    ADAPTER_2_4 = 1, ATTR_SWITCH_WIFI_2_4
    ADAPTER_5_0 = 2, ATTR_SWITCH_WIFI_5_0
    ADAPTER_5_0_GAME = 3, ATTR_SWITCH_WIFI_5_0_GAME


class DeviceAction(IntEnum):
    """DeviceAction enum"""

    def __new__(cls, value: int, phrase: str = "undefined") -> "DeviceAction":
        """New device action.

        :param value: int: action
        :param phrase: str: phrase
        :return DeviceAction
        """

        obj = int.__new__(cls, value)  # type: ignore
        obj._value_ = value

        obj.phrase = phrase  # type: ignore

        return obj

    def __str__(self) -> str:
        """Serialize to string.

        :return str
        """

        return str(self.value)

    ADD = 0, "Add"
    MOVE = 1, "Move"
    SKIP = 2, "Skip"


class Model(str, Enum):
    """Model enum"""

    def __new__(cls, value: str) -> "Model":
        """New Model.

        :param value: str: Model
        :return Model
        """

        obj = str.__new__(cls, value)  # type: ignore
        obj._value_ = value

        return obj

    def __str__(self) -> str:
        """Serialize to string.

        :return str
        """

        return str(self.value)

    NOT_KNOWN = "not_known"
    R1D = "r1d"
    R2D = "r2d"
    R1CM = "r1cm"
    R1CL = "r1cl"
    R3G = "r3g"
    R3 = "r3"
    R3P = "r3p"
    R3D = "r3d"
    R3L = "r3l"
    R3A = "r3a"
    R4C = "r4c"
    R4 = "r4"
    R4CM = "r4cm"
    R4A = "r4a"
    R4AC = "r4ac"
    D01 = "d01"
    R1350 = "r1350"
    R2100 = "r2100"
    R2350 = "r2350"
    RM2100 = "rm2100"
    R3600 = "r3600"
    RM1800 = "rm1800"
    RA50 = "ra50"
    RA67 = "ra67"
    RA69 = "ra69"
    RA71 = "ra71"
    RA81 = "ra81"
    RB03 = "rb03"
    RA80 = "ra80"
    RA82 = "ra82"
    RA72 = "ra72"
    RA70 = "ra70"
