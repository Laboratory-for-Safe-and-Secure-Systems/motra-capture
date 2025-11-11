from enum import Enum


class SchedulingModes(str, Enum):
    systemd = "systemd"
    none = "none"
