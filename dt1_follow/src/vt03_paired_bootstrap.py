from pathlib import Path
import json
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
METRICS = ROOT / "metrics"

A_FILE = METRICS / "VT03-yolo11s-per-image-ap.npy"
B_FILE = METRICS / "VT03-yolov8s-worldv2-per-image-ap.npy"
NAMES_FILE = METRICS / "VT03-paired-image-names.npy"

OUT_FILE = METRICS / "VT03-paired-bootstrap.json"

N_BOOT = 10000
SEED = 20261005


def bootstrap_mean_ci(values, rng):
    n = len(values)

    boot_means = np.empty(N_BOOT, dtype=np.float64)

    for i in range(N_BOOT):
        idx = rng.integers(0, n, size=n)
        boot_means[i] = values[idx].mean()

    low, high = np.percentile(
        boot_means,
        [2.5, 97.5]
    )

    return float(low), float(high)


def paired_bootstrap_ci(a, b, rng):
    if len(a) != len(b):
        raise ValueError("Paired arrays must have same length")

    n = len(a)

    boot_diff = np.empty(N_BOOT, dtype=np.float64)

    for i in range(N_BOOT):
        # Cùng index cho cả 2 model => paired bootstrap
        idx = rng.integers(0, n, size=n)

        boot_diff[i] = (
            a[idx].mean() - b[idx].mean()
        )

    low, high = np.percentile(
        boot_diff,
        [2.5, 97.5]
    )

    return float(low), float(high), boot_diff


def main():
    a = np.load(A_FILE)
    b = np.load(B_FILE)
    names = np.load(NAMES_FILE)

    if not (len(a) == len(b) == len(names)):
        raise ValueError("Arrays are not aligned")

    rng_a = np.random.default_rng(SEED)
    rng_b = np.random.default_rng(SEED + 1)
    rng_diff = np.random.default_rng(SEED + 2)

    a_low, a_high = bootstrap_mean_ci(
        a, rng_a
    )

    b_low, b_high = bootstrap_mean_ci(
        b, rng_b
    )

    diff_low, diff_high, boot_diff = paired_bootstrap_ci(
        a, b, rng_diff
    )

    diff = float((a - b).mean())

    # Xác suất bootstrap cho thấy YOLO11 <= YOLO-World
    prob_nonpositive = float(
        np.mean(boot_diff <= 0)
    )

    result = {
        "n_images": int(len(a)),
        "n_bootstrap": N_BOOT,
        "seed": SEED,

        "yolo11s": {
            "mean_per_image_ap": float(a.mean()),
            "ci95_low": a_low,
            "ci95_high": a_high,
            "chance_level": 0.0,
        },

        "yolov8s-worldv2": {
            "mean_per_image_ap": float(b.mean()),
            "ci95_low": b_low,
            "ci95_high": b_high,
            "chance_level": 0.0,
        },

        "paired_comparison": {
            "metric": "mean_per_image_ap_difference",
            "difference_yolo11_minus_world": diff,
            "ci95_low": diff_low,
            "ci95_high": diff_high,
            "bootstrap_prob_difference_le_0": prob_nonpositive,
        },
    }

    with OUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print("Images:", len(a))
    print("Bootstrap samples:", N_BOOT)

    print()
    print("YOLO11s")
    print("Mean:", round(float(a.mean()), 6))
    print(
        "95% CI:",
        round(a_low, 6),
        "to",
        round(a_high, 6)
    )

    print()
    print("YOLO-World")
    print("Mean:", round(float(b.mean()), 6))
    print(
        "95% CI:",
        round(b_low, 6),
        "to",
        round(b_high, 6)
    )

    print()
    print("PAIRED DIFFERENCE")
    print(
        "YOLO11 - World:",
        round(diff, 6)
    )
    print(
        "95% CI:",
        round(diff_low, 6),
        "to",
        round(diff_high, 6)
    )

    print(
        "Bootstrap P(diff <= 0):",
        round(prob_nonpositive, 6)
    )

    print()
    print("Saved:")
    print(OUT_FILE)


if __name__ == "__main__":
    main()
