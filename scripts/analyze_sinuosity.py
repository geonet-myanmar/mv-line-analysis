import csv
import json
import math
import statistics
from pathlib import Path


EARTH_RADIUS_M = 6_371_008.8
ZERO_EPSILON_M = 1e-6
SIGNIFICANT_DETOUR_THRESHOLD = 1.2


def haversine_m(point_a, point_b):
    lon1, lat1 = point_a[:2]
    lon2, lat2 = point_b[:2]

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def path_length_m(coordinates):
    return sum(
        haversine_m(coordinates[index], coordinates[index + 1])
        for index in range(len(coordinates) - 1)
    )


def classify_sinuosity(sinuosity_index):
    if math.isinf(sinuosity_index):
        return "loop_or_zero_direct_distance"
    if sinuosity_index < 1.05:
        return "near_straight"
    if sinuosity_index < 1.2:
        return "minor_detour"
    if sinuosity_index < 1.5:
        return "moderate_detour"
    return "severe_detour"


def safe_quantiles(values):
    if not values:
        return {"p50": None, "p90": None, "p95": None, "p99": None}
    ordered = sorted(values)
    return {
        "p50": statistics.median(ordered),
        "p90": ordered[min(len(ordered) - 1, math.ceil(len(ordered) * 0.90) - 1)],
        "p95": ordered[min(len(ordered) - 1, math.ceil(len(ordered) * 0.95) - 1)],
        "p99": ordered[min(len(ordered) - 1, math.ceil(len(ordered) * 0.99) - 1)],
    }


def main():
    root = Path(__file__).resolve().parent.parent
    input_path = root / "All_states_region_MVLine_tsp_level.json"
    output_dir = root / "outputs"
    output_dir.mkdir(exist_ok=True)

    data = json.loads(input_path.read_text(encoding="utf-8"))
    features = data.get("features", [])

    rows = []
    valid_sinuosity_values = []
    significant_detours = []
    region_stats = {}
    zero_direct_distance_count = 0

    for feature in features:
        geometry = feature.get("geometry") or {}
        if geometry.get("type") != "LineString":
            continue

        coordinates = geometry.get("coordinates") or []
        if len(coordinates) < 2:
            continue

        properties = feature.get("properties") or {}
        actual_length_m = path_length_m(coordinates)
        direct_length_m = haversine_m(coordinates[0], coordinates[-1])

        if direct_length_m <= ZERO_EPSILON_M:
            zero_direct_distance_count += 1
            sinuosity_index = math.inf if actual_length_m > 0 else 1.0
        else:
            sinuosity_index = actual_length_m / direct_length_m
            valid_sinuosity_values.append(sinuosity_index)

        detour_pct = None if math.isinf(sinuosity_index) else (sinuosity_index - 1) * 100
        detour_extra_km = max(0.0, (actual_length_m - direct_length_m) / 1000)
        region = properties.get("Region") or properties.get("Region_St") or "Unknown"

        row = {
            "feature_id": feature.get("id"),
            "region": region,
            "district": properties.get("District"),
            "township": properties.get("Township"),
            "ex_from": properties.get("Ex_from") or properties.get("Ext_from"),
            "ex_to": properties.get("Ex_to") or properties.get("Ext_to"),
            "kv_type": properties.get("KV_Type") or properties.get("KV_type_1"),
            "cable_type": properties.get("Cable_Type") or properties.get("Cable_ty_1"),
            "vertex_count": len(coordinates),
            "actual_length_km": round(actual_length_m / 1000, 6),
            "straight_line_km": round(direct_length_m / 1000, 6),
            "detour_extra_km": round(detour_extra_km, 6),
            "sinuosity_index": None if math.isinf(sinuosity_index) else round(sinuosity_index, 6),
            "detour_pct": None if detour_pct is None else round(detour_pct, 4),
            "classification": classify_sinuosity(sinuosity_index),
            "significant_detour": False
            if math.isinf(sinuosity_index)
            else sinuosity_index >= SIGNIFICANT_DETOUR_THRESHOLD,
        }
        rows.append(row)

        region_bucket = region_stats.setdefault(
            region,
            {
                "feature_count": 0,
                "sinuosity_values": [],
                "severe_count": 0,
                "significant_count": 0,
            },
        )
        region_bucket["feature_count"] += 1
        if not math.isinf(sinuosity_index):
            region_bucket["sinuosity_values"].append(sinuosity_index)
        if row["classification"] == "severe_detour":
            region_bucket["severe_count"] += 1
        if row["significant_detour"]:
            region_bucket["significant_count"] += 1
            significant_detours.append(row)

    valid_rows = [row for row in rows if row["sinuosity_index"] is not None]
    valid_rows.sort(key=lambda row: row["sinuosity_index"], reverse=True)
    significant_detours.sort(key=lambda row: row["sinuosity_index"], reverse=True)

    summary = {
        "input_file": str(input_path.name),
        "distance_method": "Great-circle distance (haversine) for polyline segments and endpoint distance",
        "significant_detour_threshold": SIGNIFICANT_DETOUR_THRESHOLD,
        "total_linestrings": len(rows),
        "lines_with_zero_direct_distance": zero_direct_distance_count,
        "actual_length_km": {
            "total": round(sum(row["actual_length_km"] for row in rows), 3),
            "mean": round(statistics.fmean(row["actual_length_km"] for row in rows), 3),
            "median": round(statistics.median(row["actual_length_km"] for row in rows), 3),
            "max": round(max(row["actual_length_km"] for row in rows), 3),
        },
        "straight_line_km": {
            "total": round(sum(row["straight_line_km"] for row in rows), 3),
            "mean": round(statistics.fmean(row["straight_line_km"] for row in rows), 3),
            "median": round(statistics.median(row["straight_line_km"] for row in rows), 3),
            "max": round(max(row["straight_line_km"] for row in rows), 3),
        },
        "detour_extra_km": {
            "total": round(sum(row["detour_extra_km"] for row in rows), 3),
            "mean": round(statistics.fmean(row["detour_extra_km"] for row in rows), 3),
            "median": round(statistics.median(row["detour_extra_km"] for row in rows), 3),
            "max": round(max(row["detour_extra_km"] for row in rows), 3),
        },
        "vertex_count": {
            "mean": round(statistics.fmean(row["vertex_count"] for row in rows), 3),
            "median": round(statistics.median(row["vertex_count"] for row in rows), 3),
            "max": max(row["vertex_count"] for row in rows),
        },
        "sinuosity_index": {
            "mean": round(statistics.fmean(valid_sinuosity_values), 6),
            "median": round(statistics.median(valid_sinuosity_values), 6),
            "min": round(min(valid_sinuosity_values), 6),
            "max": round(max(valid_sinuosity_values), 6),
            **{
                key: None if value is None else round(value, 6)
                for key, value in safe_quantiles(valid_sinuosity_values).items()
            },
        },
        "classification_counts": {
            label: sum(1 for row in rows if row["classification"] == label)
            for label in [
                "near_straight",
                "minor_detour",
                "moderate_detour",
                "severe_detour",
                "loop_or_zero_direct_distance",
            ]
        },
        "significant_detour_count": len(significant_detours),
        "top_20_by_sinuosity": valid_rows[:20],
        "top_20_significant_detours": significant_detours[:20],
        "region_summary": [],
    }

    for region, bucket in sorted(region_stats.items()):
        values = bucket["sinuosity_values"]
        summary["region_summary"].append(
            {
                "region": region,
                "feature_count": bucket["feature_count"],
                "mean_sinuosity": None if not values else round(statistics.fmean(values), 6),
                "median_sinuosity": None if not values else round(statistics.median(values), 6),
                "max_sinuosity": None if not values else round(max(values), 6),
                "significant_detour_count": bucket["significant_count"],
                "severe_detour_count": bucket["severe_count"],
            }
        )

    csv_path = output_dir / "mvline_sinuosity_analysis.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    json_path = output_dir / "mvline_sinuosity_summary.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Wrote {csv_path}")
    print(f"Wrote {json_path}")
    print(f"Processed {len(rows)} LineStrings")
    print(f"Significant detours (SI >= {SIGNIFICANT_DETOUR_THRESHOLD}): {len(significant_detours)}")


if __name__ == "__main__":
    main()
