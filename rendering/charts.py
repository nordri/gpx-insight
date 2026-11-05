import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import savgol_filter


THEME_COLORS = {
    "forest": {
        "line": "#d0e22a",
        "fill": "#90a91c",
        "grid": "#35561f",
        "text": "#cfe7a4",
    },
    "volcanic": {
        "line": "#ffae7f",
        "fill": "#cc5c33",
        "grid": "#5f2c1d",
        "text": "#ffd9c7",
    },
    "alpine": {
        "line": "#9be8ff",
        "fill": "#2c84a8",
        "grid": "#1f4960",
        "text": "#daf6ff",
    },
}


def _adaptive_savgol(values):
    n = len(values)
    if n < 7:
        return values

    target_window = min(41, n if n % 2 == 1 else n - 1)
    if target_window < 5:
        return values

    poly_order = 3 if target_window > 7 else 2
    return savgol_filter(values, target_window, poly_order)


# Generate elevation profile image

def generate_elevation_chart(points, theme="forest", lang="en"):
    palette = THEME_COLORS.get(theme, THEME_COLORS["forest"])
    is_es = (lang or "").lower().startswith("es")

    distances = np.asarray(
        points.get("distance_series_km") or [],
        dtype=float,
    )
    elevations = np.asarray(
        points.get("elevation_series_m") or [],
        dtype=float,
    )

    if len(distances) == 0 or len(elevations) == 0:
        raise ValueError("Missing distance/elevation series for chart generation")

    smoothed = _adaptive_savgol(elevations)

    fig, ax = plt.subplots(figsize=(9.2, 3.0), facecolor=(0, 0, 0, 0))
    ax.set_facecolor((0, 0, 0, 0))

    y_floor = float(min(smoothed.min(), elevations.min()) - 20)
    y_top = float(max(smoothed.max(), elevations.max()) + 20)

    ax.fill_between(
        distances,
        smoothed,
        y_floor,
        color=palette["fill"],
        alpha=0.32,
    )
    ax.plot(
        distances,
        smoothed,
        linewidth=2.6,
        color=palette["line"],
    )

    total_km = float(distances[-1]) if len(distances) > 1 else 0.0
    tick_step = 2 if total_km >= 8 else 1
    x_ticks = np.arange(0, total_km + 0.001, tick_step)

    ax.set_xlim(0, max(total_km, 0.1))
    ax.set_ylim(y_floor, y_top)
    ax.set_xticks(x_ticks)
    ax.set_xlabel("Distancia (km)" if is_es else "Distance (km)", color=palette["text"], fontsize=11, labelpad=10)
    ax.set_ylabel("Elevación (m)" if is_es else "Elevation (m)", color=palette["text"], fontsize=11, labelpad=10)
    ax.tick_params(axis="x", colors=palette["text"], labelsize=11)
    ax.tick_params(axis="y", colors=palette["text"], labelsize=10)
    ax.grid(True, axis="y", color=palette["grid"], alpha=0.5, linewidth=0.8)
    ax.grid(True, axis="x", color=palette["grid"], alpha=0.2, linewidth=0.6)

    for side in ["top", "right", "left", "bottom"]:
        ax.spines[side].set_visible(False)

    plt.tight_layout()

    output_path = "output/elevation_profile.png"

    plt.savefig(
        output_path,
        transparent=True,
        dpi=200
    )

    plt.close()

    return output_path