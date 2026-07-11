export type Position = [number, number];

export type FuelType = "petrol" | "diesel";
export type RouteStrategy = "cheapest_estimated" | "fastest" | "balanced";
export type PriceQualityPolicy =
  | "best_available"
  | "station_reported_only";

export interface VehicleInput {
  fuel_type: FuelType;
  fuel_grade?: string | null;
  tank_capacity: number;
  efficiency: number;
  starting_fuel: number;
  reserve_fuel: number;
}

export interface RouteRequest {
  start: string;
  finish: string;
  waypoints: string[];
  vehicle: VehicleInput;
  maximum_detour: number;
  strategy: RouteStrategy;
  price_quality: PriceQualityPolicy;
  allow_stale_prices: boolean;
}

export interface ResolvedLocation {
  query: string;
  display_name: string;
  latitude: number;
  longitude: number;
}

export interface FuelStop {
  sequence: number;
  station_id: string;
  name: string;
  address: string;
  city: string;
  state: string;
  latitude: number;
  longitude: number;
  route_distance: number;
  distance_to_route: number;
  unit_price: number;
  price: {
    label: "live" | "reported" | "reference" | "estimated" | "stale";
    geographic_precision: "station" | "city" | "district" | "state";
    confidence: "high" | "medium" | "low";
    as_of: string;
    expires_at: string;
    observation_ids: string[];
    resolver_version: string;
  };
  fuel_on_arrival: number;
  volume: number;
  cost: number;
}

interface GeoJsonGeometry {
  type: "LineString" | "Point";
  coordinates: number[] | number[][];
}

export interface GeoJsonFeature {
  type: "Feature";
  geometry: GeoJsonGeometry;
  properties: {
    kind: "route" | "fuel_stop";
    sequence?: number;
    name?: string;
    unit_price?: number;
    price_label?: string;
    distance?: number;
    distance_unit?: string;
  };
}

export interface RoutePlan {
  api_version: "v2";
  market: {
    code: string;
    country_code: string;
    country_name: string;
    currency_code: string;
    distance_unit: string;
    volume_unit: string;
    efficiency_unit: string;
  };
  start: ResolvedLocation;
  finish: ResolvedLocation;
  waypoints: ResolvedLocation[];
  route: {
    distance: number;
    duration_hours: number;
    geojson: {
      type: "FeatureCollection";
      features: GeoJsonFeature[];
    };
  };
  vehicle: {
    fuel_type: FuelType;
    fuel_grade: string | null;
    tank_capacity: number;
    efficiency: number;
    starting_fuel: number;
    reserve_fuel: number;
    maximum_range: number;
    maximum_station_detour: number;
  };
  fuel_plan: {
    starting_fuel: number;
    reserve_fuel: number;
    stops: FuelStop[];
    total_consumed_volume: number;
    purchased_volume: number;
    purchase_cost: number;
    arrival_fuel: number;
    currency: string;
  };
  comparisons: Array<{
    alternative: number;
    distance: number;
    duration_hours: number;
    fuel_stops: number;
    purchase_cost: number;
    selection_score: number;
    requested_strategy: RouteStrategy;
  }>;
  data_quality: {
    station_snapshot: string;
    station_snapshot_generated_at: string | null;
    observation_watermark: number;
    required_stop_quotes: number;
    resolved_stop_quotes: number;
    price_coverage_percent: number;
    label_counts: Record<string, number>;
    confidence_counts: Record<string, number>;
    oldest_price_as_of: string | null;
    warning: string;
  };
  metadata: {
    strategy: RouteStrategy;
    price_quality_policy: PriceQualityPolicy;
    route_alternatives_evaluated: number;
    feasible_route_alternatives: number;
    selected_alternative: number;
    selection_score: number;
    routing_provider: string;
    geocoding_provider: string;
    detour_validation: "estimated" | "validated";
    station_attribution: string;
  };
}

export interface ApiError {
  error: {
    code: string;
    message: string;
  };
}
