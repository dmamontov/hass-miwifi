"""Enums."""

from __future__ import annotations

from enum import Enum, IntEnum

from homeassistant.backports.enum import StrEnum

from .const import (
    ATTR_SWITCH_WIFI_2_4,
    ATTR_SWITCH_WIFI_5_0,
    ATTR_SWITCH_WIFI_5_0_GAME,
    ATTR_SWITCH_WIFI_GUEST,
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
    WL14 = "wl14", ATTR_SWITCH_WIFI_GUEST


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


class EncryptionAlgorithm(StrEnum):
    """EncryptionAlgorithm enum"""

    SHA1 = "sha1"
    SHA256 = "sha256"


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
    R1D = "r1d"  # 2014
    R1CM = "r1cm"  # 2014
    R1CL = "r1cl"  # 2015
    R2D = "r2d"  # 2015.08
    R3 = "r3"  # 2016
    R3G = "r3g"  # 2017.03
    R3P = "r3p"  # 2017
    R3D = "r3d"  # 2017
    R3L = "r3l"  # 2017
    R3A = "r3a"  # 2017.11.16
    R4 = "r4"  # 2019.11.26
    R4C = "r4c"  # 2019.11.26
    R4CM = "r4cm"  # 2019.11.26
    R4A = "r4a"  # 2019.11.26
    R4AC = "r4ac"  # 2019.11.26
    D01 = "d01"  # 2019.11.26
    R2100 = "r2100"  # 2019.11.26
    RM2100 = "rm2100"  # 2019
    R3600 = "r3600"  # 2020.03.01
    RM1800 = "rm1800"  # 2020.05
    RA67 = "ra67"  # 2020.06.19
    R2350 = "r2350"  # 2020.07.02
    R1350 = "r1350"  # 2020.07.03
    RA69 = "ra69"  # 2020.08.11
    RA72 = "ra72"  # 2021.01.08
    RA50 = "ra50"  # 2021.01.28
    RA70 = "ra70"  # 2021.03.30
    CR6606 = "cr6606"  # 2021.04.25
    RA81 = "ra81"  # 2021.07.27
    RA80 = "ra80"  # 2021.08.11
    RB03 = "rb03"  # 2021.09.27
    RA71 = "ra71"  # 2021.10.22
    RB01 = "rb01"  # 2021.10.28
    RA82 = "ra82"  # 2021.11.01
    CR8808 = "cr8808"  # 2021.11.26
    RB04 = "rb04"  # 2022.02.17
    RA74 = "ra74"  # 2022.03.18
    RB06 = "rb06"  # 2022.04.02
    RB08 = "rb08"  # 2022.07.04
