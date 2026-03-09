# MV Line Morphometric and Sinuosity Analysis

This project performs a morphometric and routing-efficiency analysis on medium-voltage transmission/distribution line geometries stored in `All_states_region_MVLine_tsp_level.json`.

The main objective is to calculate the **Sinuosity Index (SI)** for every `LineString` in the dataset:

```text
Sinuosity Index = Actual Path Length / Straight-Line Distance
```

This metric helps identify line segments that deviate strongly from the most direct path and may indicate terrain constraints, settlement avoidance, network topology constraints, or inefficient routing.

## Project Goals

- Compute the actual polyline length for each MV line segment.
- Compute the straight-line endpoint distance for the same segment.
- Derive a per-feature **Sinuosity Index**.
- Flag segments with significant detours.
- Export reproducible analysis outputs for further GIS, spreadsheet, or statistical work.
- Summarize network-wide morphometric characteristics such as length distribution and vertex complexity.

## Repository Structure

```text
.
|-- All_states_region_MVLine_tsp_level.json
|-- README.md
|-- outputs/
|   |-- mvline_sinuosity_analysis.csv
|   `-- mvline_sinuosity_summary.json
`-- scripts/
    `-- analyze_sinuosity.py
```

## Input Data

### Source File

- `All_states_region_MVLine_tsp_level.json`

### Format

The input is a GeoJSON `FeatureCollection` containing `LineString` features. Each feature typically includes:

- `geometry.coordinates`: ordered longitude/latitude vertices, sometimes with a third Z value.
- `properties`: descriptive attributes such as `Ex_from`, `Ex_to`, `Region`, `District`, `Township`, `KV_Type`, and `Cable_Type`.

### Geometry Assumption

The coordinates are stored in geographic coordinates (`longitude`, `latitude`). For that reason, this project does **not** use simple planar Euclidean distance on raw degrees. Instead, it computes **great-circle distances** using the haversine formula so all lengths are expressed in meters/kilometers on the earth’s surface.

## Methodology

### 1. Actual Path Length

For each `LineString`, the script sums the great-circle distance between every consecutive pair of vertices:

```text
Actual Path Length = sum(distance(vertex_i, vertex_i+1))
```

This captures the real routed path represented by the geometry.

### 2. Straight-Line Distance

The script computes the great-circle distance between the first and last coordinate in the `LineString`:

```text
Straight-Line Distance = distance(start_point, end_point)
```

This is the shortest direct route between the line endpoints.

### 3. Sinuosity Index

The routing efficiency metric is:

```text
SI = Actual Path Length / Straight-Line Distance
```

Interpretation:

- `SI = 1.0`: perfectly straight segment.
- `SI > 1.0`: routed path is longer than the direct connection.
- Larger SI values indicate stronger detours or more sinuous geometry.

### 4. Additional Derived Metrics

The script also computes:

- `detour_extra_km`: actual length minus straight-line distance.
- `detour_pct`: percent increase above direct distance.
- `vertex_count`: number of vertices in the `LineString`.
- `classification`: qualitative sinuosity class.
- `significant_detour`: boolean flag for high-detour segments.

### 5. Classification Rules

Each line is assigned one class:

- `near_straight`: `SI < 1.05`
- `minor_detour`: `1.05 <= SI < 1.2`
- `moderate_detour`: `1.2 <= SI < 1.5`
- `severe_detour`: `SI >= 1.5`
- `loop_or_zero_direct_distance`: start and end points coincide, so the ratio is undefined or infinite

### 6. Significant Detour Threshold

This project flags a segment as a **significant detour** when:

```text
SI >= 1.2
```

That threshold is implemented in the analysis script as:

```python
SIGNIFICANT_DETOUR_THRESHOLD = 1.2
```

## Implementation

### Script

- `scripts/analyze_sinuosity.py`

### Dependencies

The script uses only Python standard-library modules:

- `csv`
- `json`
- `math`
- `statistics`
- `pathlib`

No third-party packages are required.

### Python Version

Python 3.10+ is recommended.

## How To Run

From the repository root:

```bash
python scripts/analyze_sinuosity.py
```

The script will:

1. Read `All_states_region_MVLine_tsp_level.json`
2. Calculate all per-line metrics
3. Create the `outputs/` directory if it does not already exist
4. Write:
   - `outputs/mvline_sinuosity_analysis.csv`
   - `outputs/mvline_sinuosity_summary.json`

## Output Files

### 1. `outputs/mvline_sinuosity_analysis.csv`

This is the per-feature analysis table. Each row represents one `LineString`.

Key columns:

- `feature_id`: original feature identifier
- `region`
- `district`
- `township`
- `ex_from`
- `ex_to`
- `kv_type`
- `cable_type`
- `vertex_count`
- `actual_length_km`
- `straight_line_km`
- `detour_extra_km`
- `sinuosity_index`
- `detour_pct`
- `classification`
- `significant_detour`

This file is best for filtering, ranking, mapping, and downstream analysis in Excel, Power BI, Python, or GIS tools.

### 2. `outputs/mvline_sinuosity_summary.json`

This is the aggregated analysis summary. It includes:

- global dataset statistics
- length summaries
- sinuosity distribution statistics
- classification counts
- significant detour count
- top segments ranked by sinuosity
- top significant detours
- region-level summary statistics

## Headline Results

These values were generated from the current dataset in this repository.

### Dataset Scale

- Total `LineString` features analyzed: `2323`
- Total actual routed length: `17,844.600 km`
- Total direct endpoint length: `15,866.971 km`
- Total extra routed distance: `1,977.629 km`

### Morphometric Summary

- Mean segment length: `7.682 km`
- Median segment length: `2.528 km`
- Maximum segment length: `222.648 km`
- Mean vertex count: `3.576`
- Median vertex count: `2`
- Maximum vertex count: `43`

### Sinuosity Summary

- Mean SI: `1.086199`
- Median SI: `1.000000`
- Minimum SI: `1.000000`
- Maximum SI: `5.451898`
- 90th percentile SI: `1.254127`
- 95th percentile SI: `1.413492`
- 99th percentile SI: `1.944758`

### Classification Counts

- `near_straight`: `1669`
- `minor_detour`: `339`
- `moderate_detour`: `223`
- `severe_detour`: `91`
- `loop_or_zero_direct_distance`: `1`

### Significant Detours

- Segments with `SI >= 1.2`: `314`

## Highest Sinuosity Segments

Top examples by Sinuosity Index:

| Rank | Feature ID | Region | Township | From | To | SI | Actual km | Direct km |
|---|---|---|---|---|---|---:|---:|---:|
| 1 | `All_states_region_MVLine_tsp_level.791` | Unknown | - | - | - | 5.451898 | 11.310 | 2.075 |
| 2 | `All_states_region_MVLine_tsp_level.588` | Bago | Thayarwady | Thonse | Plate factory | 5.027636 | 12.037 | 2.394 |
| 3 | `All_states_region_MVLine_tsp_level.1058` | Mandalay | Amarapura | - | - | 4.962667 | 2.713 | 0.547 |
| 4 | `All_states_region_MVLine_tsp_level.1422` | Mon | Kyaikmayaw | - | - | 4.574335 | 4.613 | 1.008 |
| 5 | `All_states_region_MVLine_tsp_level.1968` | ShanN | Hsipaw | - | - | 4.047491 | 3.458 | 0.854 |

## Largest Absolute Detours

Some segments may not have the highest ratio, but still add large absolute extra distance. These are operationally important:

| Rank | Feature ID | Region | Township | From | To | Extra km | SI | Actual km | Direct km |
|---|---|---|---|---|---|---:|---:|---:|---:|
| 1 | `All_states_region_MVLine_tsp_level.766` | Unknown | - | Beluchaung | Hpasawng | 38.210 | 1.500714 | 114.520 | 76.311 |
| 2 | `All_states_region_MVLine_tsp_level.47` | Ayeyarwady | Maubin | Kyaunggon | Pantanaw | 33.966 | 3.195795 | 49.435 | 15.469 |
| 3 | `All_states_region_MVLine_tsp_level.1632` | Kawlin | - | ACSR 70mm2 | Kanbaly | 31.261 | 1.538505 | 89.311 | 58.051 |
| 4 | `All_states_region_MVLine_tsp_level.958` | Unknown | - | - | - | 28.988 | 1.852428 | 62.995 | 34.007 |
| 5 | `All_states_region_MVLine_tsp_level.1989` | ShanS | Nansang | Kengtawng | Kalaw | 26.515 | 1.303989 | 113.737 | 87.222 |

## Regional Pattern Summary

Regions or region-like labels with the highest counts of significant detours in the current data include:

- `Unknown`: `138`
- `Mandalay`: `66`
- `Bago`: `49`
- `Naypyitaw`: `26`
- `ShanS`: `10`

Some smaller groups have high mean sinuosity but very low feature counts, so they should be interpreted cautiously.

## Edge Cases and Data Quality Notes

### Zero Direct Distance

One feature has the same start and end location, which makes the direct distance zero:

- `All_states_region_MVLine_tsp_level.2185`

It is labeled `loop_or_zero_direct_distance` and excluded from numeric SI ranking.

### Missing Attributes

Some features contain missing values in:

- `Region`
- `District`
- `Township`
- `Ex_from`
- `Ex_to`

Where regional attributes are absent, the script falls back to `Region_St`, otherwise it uses `Unknown`.

### Ratio Interpretation

Very high SI values are sometimes produced by short segments where the start and end points are close together. For planning or engineering prioritization, it is useful to review:

- **relative inefficiency** using `sinuosity_index`
- **absolute inefficiency** using `detour_extra_km`

Both are included in the outputs for that reason.

## Use Cases

This analysis can support:

- routing-efficiency assessment
- feeder/network design review
- anomaly detection in geometry data
- prioritization of segments for field validation
- comparison of topological complexity across regions
- feature engineering for further spatial or asset analysis

## Reproducibility

To reproduce the published results:

1. Clone the repository.
2. Ensure Python 3.10+ is installed.
3. Run `python scripts/analyze_sinuosity.py`.
4. Compare regenerated files in `outputs/` with the committed outputs.

Because the script is deterministic and uses only standard-library functions, repeated runs on the same input should produce the same outputs.

## Customization

You can adapt the project easily:

- Change `SIGNIFICANT_DETOUR_THRESHOLD` to tighten or relax detour flagging.
- Add new regional or voltage-level group summaries from the existing CSV columns.
- Extend the script to export GeoJSON with derived attributes for direct mapping.
- Integrate the outputs into dashboards or notebooks.

## Limitations

- Great-circle distance is appropriate for geographic coordinates, but it is still an approximation compared with full projected-geodesic workflows.
- The analysis is geometry-based only; it does not incorporate terrain, land cover, road corridors, right-of-way restrictions, or engineering constraints.
- Missing attribute values limit some regional or asset-specific interpretation.
- Sinuosity alone does not indicate whether a route is bad; some detours are expected and necessary.

## License and Data Governance

Before publishing publicly on GitHub, verify:

- you are authorized to publish the source dataset
- attribute names and place names are safe to disclose
- any organizational or utility restrictions on infrastructure data have been reviewed

If needed, keep the script public and store the raw dataset privately.

## Suggested Citation

If you want to cite the repository in reports or presentations, use a format like:

```text
MV Line Morphometric and Sinuosity Analysis. GitHub repository. Analysis of LineString routing efficiency from All_states_region_MVLine_tsp_level.json.
```

## Maintainer Notes

If this repository evolves, likely next steps are:

- add unit tests for distance and classification logic
- add GeoJSON output with joined metrics
- add plots for SI distribution and regional comparisons
- add notebook-based exploratory visualizations
