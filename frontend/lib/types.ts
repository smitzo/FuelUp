export type Position = [number, number];

export interface ResolvedLocation {
  query: string;
  display_name: string;
  latitude: number;
  longitude: number;
}

export interface FuelStop {
  sequence: number;
  opis_id: string;
  name: string;
  address: string;
  city: string;
  state: string;
  latitude: number;
  longitude: number;
  route_mile: number;
  distance_to_route_miles: number;
  price_per_gallon_usd: number;
  fuel_on_arrival_gallons: number;
  gallons: number;
  cost_usd: number;
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
    price_per_gallon_usd?: number;
    distance_miles?: number;
  };
}

export interface RoutePlan {
  start: ResolvedLocation;
  finish: ResolvedLocation;
  route: {
    distance_miles: number;
    duration_hours: number;
    geojson: {
      type: "FeatureCollection";
      features: GeoJsonFeature[];
    };
  };
  vehicle: {
    maximum_range_miles: number;
    fuel_economy_mpg: number;
    tank_capacity_gallons: number;
  };
  fuel_plan: {
    initial_fuel_estimate: {
      gallons: number;
      cost_usd: number;
      price_reference: {
        opis_id: string;
        name: string;
        city: string;
        state: string;
        price_per_gallon_usd: number;
      };
    };
    stops: FuelStop[];
    total_gallons: number;
    total_cost_usd: number;
    currency: "USD";
  };
  metadata: {
    external_calls: string;
    routing_provider: string;
    geocoding_provider: string;
    station_coordinate_accuracy: string;
    route_alternatives_evaluated: number;
    feasible_route_alternatives: number;
    selection_score_usd: number;
    selection_policy: string;
    assumption: string;
  };
}

export interface ApiError {
  error: {
    code: string;
    message: string;
  };
}
