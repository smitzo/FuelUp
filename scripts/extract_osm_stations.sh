#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 INPUT.osm.pbf OUTPUT.geojson" >&2
  exit 2
fi

if ! command -v osmium >/dev/null 2>&1; then
  echo "osmium-tool is required for reproducible PBF filtering." >&2
  exit 1
fi

input_path=$1
output_path=$2
filtered_path="${output_path%.geojson}.osm.pbf"

osmium tags-filter "$input_path" nwr/amenity=fuel -o "$filtered_path" --overwrite
osmium export "$filtered_path" -o "$output_path" --overwrite
echo "Created market-neutral station input at $output_path from OSM features."
