"""Pure helpers for the benchmark's frame-time statistics."""

import math


def summarize_frame_times(dt_ms_list):
    """Return the benchmark FPS and frame-time metrics for measured frames."""
    frame_count = len(dt_ms_list)
    if not frame_count:
        return {
            "avg_fps": 0.0,
            "p1_low_fps": 0.0,
            "frame_ms_p95": 0.0,
            "frames": 0,
        }

    total_ms = sum(dt_ms_list)
    avg_fps = 1000.0 * frame_count / total_ms if total_ms > 0 else 0.0
    slowest_count = max(1, math.ceil(0.01 * frame_count))
    slowest_frames = sorted(dt_ms_list, reverse=True)[:slowest_count]
    slowest_average_ms = sum(slowest_frames) / len(slowest_frames)
    p1_low_fps = 1000.0 / slowest_average_ms if slowest_average_ms > 0 else 0.0
    ordered = sorted(dt_ms_list)
    p95_index = min(frame_count - 1, int(0.95 * (frame_count - 1)))

    return {
        "avg_fps": avg_fps,
        "p1_low_fps": p1_low_fps,
        "frame_ms_p95": ordered[p95_index],
        "frames": frame_count,
    }
