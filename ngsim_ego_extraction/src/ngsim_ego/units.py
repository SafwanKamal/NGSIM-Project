from __future__ import annotations

FEET_TO_METERS = 0.3048


def position_factor(units_config: dict) -> float:
    original = units_config.get("original_position", "feet")
    output = units_config.get("output_position", "meters")
    if original == output:
        return 1.0
    if original == "feet" and output == "meters":
        return FEET_TO_METERS
    raise ValueError(f"Unsupported position unit conversion: {original!r} to {output!r}")


def speed_factor(units_config: dict) -> float:
    original = units_config.get("original_speed", "feet_per_second")
    output = units_config.get("output_speed", "meters_per_second")
    if original == output:
        return 1.0
    if original == "feet_per_second" and output == "meters_per_second":
        return FEET_TO_METERS
    raise ValueError(f"Unsupported speed unit conversion: {original!r} to {output!r}")


def acceleration_factor(units_config: dict) -> float:
    return speed_factor(units_config)

