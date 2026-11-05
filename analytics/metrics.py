from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from math import atan2, cos, radians, sin, sqrt


EARTH_RADIUS = 6371000


DIFFICULTY_LEVELS = [
    (20, "EASY"),
    (40, "MODERATE"),
    (60, "HARD"),
    (80, "VERY HARD"),
    (999, "BRUTAL")
]


UPHILL_BUCKETS = [
    ("gt15", "> 15%", lambda g: g > 15),
    ("10_15", "10-15%", lambda g: 10 < g <= 15),
    ("5_10", "5-10%", lambda g: 5 < g <= 10),
    ("1_5", "1-5%", lambda g: 1 <= g <= 5),
]


DOWNHILL_BUCKETS = [
    ("1_5", "1-5%", lambda g: -5 <= g <= -1),
    ("5_10", "5-10%", lambda g: -10 <= g < -5),
    ("10_15", "10-15%", lambda g: -15 <= g < -10),
    ("gt15", "> 15%", lambda g: g < -15),
]


def _safe_seconds(delta: timedelta | None) -> float:
    if not delta:
        return 0.0
    return max(delta.total_seconds(), 0.0)


def _format_hhmmss(seconds: float) -> str:
    return str(timedelta(seconds=int(max(seconds, 0))))


def _format_hhmm(timestamp) -> str:
    return timestamp.strftime("%H:%M") if timestamp else "--:--"


def _accumulate_bucket_distance(
    buckets: list[tuple[str, str, Callable[[float], bool]]],
    grade: float,
    distance: float,
    target: dict[str, float],
) -> None:
    for key, _, rule in buckets:
        if rule(grade):
            target[key] += distance
            return


# Haversine distance in meters

def haversine(lat1, lon1, lat2, lon2):
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2 +
        cos(radians(lat1)) *
        cos(radians(lat2)) *
        sin(dlon / 2) ** 2
    )

    return 2 * EARTH_RADIUS * atan2(sqrt(a), sqrt(1 - a))


# Compute route metrics

def compute_basic_metrics(points):
    if not points:
        raise ValueError("GPX route must contain at least one point")

    # Reject isolated GPS excursions only when both adjacent legs imply
    # impossible speeds and the bridge between neighbours is plausible.
    # Do not silently bridge genuine recording gaps.
    cleaned = list(points)
    idx = 1
    while idx < len(cleaned) - 1:
        a, b, c = cleaned[idx - 1:idx + 2]
        ta, tb, tc = (p.get("time") for p in (a, b, c))
        if ta is not None and tb is not None and tc is not None:
            dt1 = (tb - ta).total_seconds()
            dt2 = (tc - tb).total_seconds()
            dt_bridge = (tc - ta).total_seconds()
            if dt1 > 0 and dt2 > 0:
                d1 = haversine(a["lat"], a["lon"], b["lat"], b["lon"])
                d2 = haversine(b["lat"], b["lon"], c["lat"], c["lon"])
                bridge = haversine(a["lat"], a["lon"], c["lat"], c["lon"])
                if (d1 / dt1 * 3.6 > 100 and d2 / dt2 * 3.6 > 100
                        and bridge / dt_bridge * 3.6 <= 250
                        and d1 + d2 > max(bridge * 3, bridge + 100)):
                    cleaned.pop(idx)
                    continue
        idx += 1
    points = cleaned

    total_distance = 0
    elevation_gain = 0
    elevation_loss = 0
    # Track confirmed changes between elevation extrema. A 3 m reversal
    # suppresses small alternating GPS altitude noise without losing gradual climbs.
    elevation_deadband_m = 3.0
    elevation_anchor = float(points[0]["ele"])
    elevation_extreme = elevation_anchor
    elevation_direction = 0

    speeds = []
    stopped_seconds = 0
    timed_distance = 0.0

    distance_series_km = [0.0]
    elevation_series_m = [float(points[0]["ele"])]

    uphill_distances = {key: 0.0 for key, _, _ in UPHILL_BUCKETS}
    downhill_distances = {key: 0.0 for key, _, _ in DOWNHILL_BUCKETS}
    flat_distance = 0.0

    max_up_grade = 0.0
    max_down_grade = 0.0
    up_grade_weighted_sum = 0.0
    up_grade_distance = 0.0
    down_grade_weighted_sum = 0.0
    down_grade_distance = 0.0
    grade_chunk_distance = 0.0
    grade_chunk_ele = 0.0

    highest_point = max(points, key=lambda p: p["ele"])
    min_ele = points[0]["ele"]
    max_ele = points[0]["ele"]

    for i in range(1, len(points)):
        prev = points[i - 1]
        curr = points[i]

        distance = haversine(
            prev["lat"],
            prev["lon"],
            curr["lat"],
            curr["lon"]
        )

        total_distance += distance
        distance_series_km.append(total_distance / 1000)

        delta_ele = curr["ele"] - prev["ele"]
        elevation_series_m.append(float(curr["ele"]))

        min_ele = min(min_ele, curr["ele"])
        max_ele = max(max_ele, curr["ele"])

        altitude = float(curr["ele"])
        if elevation_direction == 0:
            if altitude >= elevation_anchor + elevation_deadband_m:
                elevation_direction = 1
                elevation_extreme = altitude
            elif altitude <= elevation_anchor - elevation_deadband_m:
                elevation_direction = -1
                elevation_extreme = altitude
        elif elevation_direction == 1:
            if altitude > elevation_extreme:
                elevation_extreme = altitude
            elif altitude <= elevation_extreme - elevation_deadband_m:
                elevation_gain += elevation_extreme - elevation_anchor
                elevation_anchor = elevation_extreme
                elevation_extreme = altitude
                elevation_direction = -1
        else:
            if altitude < elevation_extreme:
                elevation_extreme = altitude
            elif altitude >= elevation_extreme + elevation_deadband_m:
                elevation_loss += elevation_anchor - elevation_extreme
                elevation_anchor = elevation_extreme
                elevation_extreme = altitude
                elevation_direction = 1

        grade_chunk_distance += distance
        grade_chunk_ele += delta_ele

        if grade_chunk_distance >= 20:
            grade_pct = (grade_chunk_ele / grade_chunk_distance) * 100
            grade_pct = max(min(grade_pct, 45.0), -45.0)

            if grade_pct >= 1:
                _accumulate_bucket_distance(
                    UPHILL_BUCKETS,
                    grade_pct,
                    grade_chunk_distance,
                    uphill_distances,
                )
                up_grade_weighted_sum += grade_pct * grade_chunk_distance
                up_grade_distance += grade_chunk_distance
                max_up_grade = max(max_up_grade, grade_pct)
            elif grade_pct <= -1:
                _accumulate_bucket_distance(
                    DOWNHILL_BUCKETS,
                    grade_pct,
                    grade_chunk_distance,
                    downhill_distances,
                )
                down_grade_weighted_sum += grade_pct * grade_chunk_distance
                down_grade_distance += grade_chunk_distance
                max_down_grade = min(max_down_grade, grade_pct)
            else:
                flat_distance += grade_chunk_distance

            grade_chunk_distance = 0.0
            grade_chunk_ele = 0.0

        if prev["time"] and curr["time"]:
            delta_time = (
                curr["time"] - prev["time"]
            ).total_seconds()

            if delta_time > 0:
                speed_kmh = (distance / delta_time) * 3.6
                # Exclude implausible instantaneous speeds from speed statistics.
                # This is a provisional hiking/trail-running threshold, not a
                # universal GPS outlier detector; distance still includes the leg.
                if speed_kmh <= 100:
                    speeds.append(speed_kmh)
                timed_distance += distance

                if speed_kmh < 0.7:
                    stopped_seconds += delta_time

    if grade_chunk_distance > 0:
        grade_pct = (grade_chunk_ele / grade_chunk_distance) * 100
        grade_pct = max(min(grade_pct, 45.0), -45.0)

        if grade_pct >= 1:
            _accumulate_bucket_distance(
                UPHILL_BUCKETS,
                grade_pct,
                grade_chunk_distance,
                uphill_distances,
            )
            up_grade_weighted_sum += grade_pct * grade_chunk_distance
            up_grade_distance += grade_chunk_distance
            max_up_grade = max(max_up_grade, grade_pct)
        elif grade_pct <= -1:
            _accumulate_bucket_distance(
                DOWNHILL_BUCKETS,
                grade_pct,
                grade_chunk_distance,
                downhill_distances,
            )
            down_grade_weighted_sum += grade_pct * grade_chunk_distance
            down_grade_distance += grade_chunk_distance
            max_down_grade = min(max_down_grade, grade_pct)
        else:
            flat_distance += grade_chunk_distance

    if elevation_direction == 1:
        elevation_gain += elevation_extreme - elevation_anchor
    elif elevation_direction == -1:
        elevation_loss += elevation_anchor - elevation_extreme

    start_time = points[0]["time"]
    end_time = points[-1]["time"]

    has_timestamps = bool(start_time and end_time) and all(
        p.get("time") is not None for p in points
    ) and all(
        points[i]["time"] > points[i - 1]["time"]
        for i in range(1, len(points))
    )
    total_seconds = _safe_seconds(end_time - start_time) if has_timestamps else 0.0
    moving_seconds = max(total_seconds - stopped_seconds, 0.0)

    avg_speed = (
        (total_distance / 1000) /
        (moving_seconds / 3600)
    ) if moving_seconds > 0 else 0

    avg_speed_total = (
        (total_distance / 1000) /
        (total_seconds / 3600)
    ) if total_seconds > 0 else avg_speed

    # Time-derived metrics are unknown when chronology is missing or invalid.
    if not has_timestamps:
        avg_speed = None
        avg_speed_total = None
        max_speed = None
    else:
        max_speed = max(speeds) if speeds else None

    steep_ratio = min(elevation_gain / max(total_distance, 1), 1)

    difficulty_score = (
        (total_distance / 1000) * 1.0 +
        elevation_gain * 0.015 +
        steep_ratio * 20
    )

    difficulty_label = next(
        label for threshold, label in DIFFICULTY_LEVELS
        if difficulty_score <= threshold
    )

    uphill_total = sum(uphill_distances.values())
    downhill_total = sum(downhill_distances.values())

    def pct_of_route(distance_m: float) -> float:
        return (distance_m / total_distance) * 100 if total_distance > 0 else 0.0

    ascent_per_km = elevation_gain / max(total_distance / 1000, 0.001)
    descent_per_km = elevation_loss / max(total_distance / 1000, 0.001)

    uphill_table = [
        {
            "key": key,
            "label": label,
            "distance_km": round(uphill_distances[key] / 1000, 2),
            "route_pct": round(pct_of_route(uphill_distances[key]), 1),
        }
        for key, label, _ in UPHILL_BUCKETS
    ]

    downhill_table = [
        {
            "key": key,
            "label": label,
            "distance_km": round(downhill_distances[key] / 1000, 2),
            "route_pct": round(pct_of_route(downhill_distances[key]), 1),
        }
        for key, label, _ in DOWNHILL_BUCKETS
    ]

    return {
        "distance_km": round(total_distance / 1000, 1),
        "elevation_gain_m": int(elevation_gain),
        "elevation_loss_m": int(elevation_loss),
        "total_time": _format_hhmmss(total_seconds) if has_timestamps else None,
        "moving_time": _format_hhmmss(moving_seconds) if has_timestamps else None,
        "stopped_time": _format_hhmmss(stopped_seconds) if has_timestamps else None,
        "avg_speed": round(avg_speed, 1) if avg_speed is not None else None,
        "avg_speed_total": round(avg_speed_total, 1) if avg_speed_total is not None else None,
        "avg_speed_moving": round(avg_speed, 1) if avg_speed is not None else None,
        "max_speed": round(max_speed, 1) if max_speed is not None else None,
        "highest_point": int(highest_point["ele"]),
        "difficulty_score": int(difficulty_score),
        "difficulty_label": difficulty_label,
        "start_time": _format_hhmm(start_time),
        "end_time": _format_hhmm(end_time),
        "has_timestamps": has_timestamps,
        "elevation_min_m": int(min_ele),
        "elevation_max_m": int(max_ele),
        "elevation_start_m": int(points[0]["ele"]),
        "elevation_end_m": int(points[-1]["ele"]),
        "uphill_ratio_pct": round(pct_of_route(uphill_total), 1),
        "downhill_ratio_pct": round(pct_of_route(downhill_total), 1),
        "flat_ratio_pct": round(pct_of_route(flat_distance), 1),
        "uphill_distance_km": round(uphill_total / 1000, 2),
        "downhill_distance_km": round(downhill_total / 1000, 2),
        "flat_distance_km": round(flat_distance / 1000, 2),
        "ascent_per_km": round(ascent_per_km, 1),
        "descent_per_km": round(descent_per_km, 1),
        "max_up_grade_pct": round(max_up_grade, 1),
        "max_down_grade_pct": round(abs(max_down_grade), 1),
        "avg_up_grade_pct": round(
            up_grade_weighted_sum / up_grade_distance,
            1,
        ) if up_grade_distance > 0 else 0.0,
        "avg_down_grade_pct": round(
            down_grade_weighted_sum / down_grade_distance,
            1,
        ) if down_grade_distance > 0 else 0.0,
        "uphill_table": uphill_table,
        "downhill_table": downhill_table,
        "distance_series_km": [round(v, 4) for v in distance_series_km],
        "elevation_series_m": [round(v, 2) for v in elevation_series_m],
        "distance_total_m": int(total_distance),
        "distance_timed_m": int(timed_distance),
        "point_count": len(points),
    }