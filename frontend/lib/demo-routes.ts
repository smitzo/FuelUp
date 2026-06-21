import type { FuelStop, RoutePlan } from "@/lib/types";

type Coordinate = [longitude: number, latitude: number];

interface DemoRouteDefinition {
  id: string;
  region: string;
  start: {
    name: string;
    state: string;
    coordinate: Coordinate;
  };
  finish: {
    name: string;
    state: string;
    coordinate: Coordinate;
  };
  distanceMiles: number;
  durationHours: number;
  basePrice: number;
  waypoints: Coordinate[];
}

export interface DemoRouteOption {
  id: string;
  label: string;
  region: string;
  distanceMiles: number;
  durationHours: number;
}

const demoDefinitions: DemoRouteDefinition[] = [
  route("los-angeles-new-york", "Cross-country", "Los Angeles", "CA", [-118.2437, 34.0522], "New York", "NY", [-74.006, 40.7128], 2780, 41, 3.34, [[-115.1398, 36.1699], [-112.074, 33.4484], [-104.9903, 39.7392], [-94.5786, 39.0997], [-87.6298, 41.8781], [-79.9959, 40.4406]]),
  route("seattle-miami", "Cross-country", "Seattle", "WA", [-122.3321, 47.6062], "Miami", "FL", [-80.1918, 25.7617], 3300, 49, 3.29, [[-116.2023, 43.615], [-111.891, 40.7608], [-104.9903, 39.7392], [-97.5164, 35.4676], [-90.0715, 29.9511], [-84.388, 33.749]]),
  route("new-york-miami", "East Coast", "New York", "NY", [-74.006, 40.7128], "Miami", "FL", [-80.1918, 25.7617], 1280, 19, 3.21, [[-75.1652, 39.9526], [-77.0369, 38.9072], [-78.6382, 35.7796], [-80.8431, 35.2271], [-81.6557, 30.3322], [-81.3792, 28.5383]]),
  route("boston-washington", "East Coast", "Boston", "MA", [-71.0589, 42.3601], "Washington", "DC", [-77.0369, 38.9072], 440, 7.5, 3.27, [[-72.6734, 41.7658], [-73.1952, 41.3083], [-74.006, 40.7128], [-75.1652, 39.9526], [-76.6122, 39.2904]]),
  route("atlanta-orlando", "Southeast", "Atlanta", "GA", [-84.388, 33.749], "Orlando", "FL", [-81.3792, 28.5383], 440, 6.5, 3.12, [[-83.6324, 32.8407], [-83.2785, 30.8327], [-82.3248, 29.6516]]),
  route("nashville-new-orleans", "Southeast", "Nashville", "TN", [-86.7816, 36.1627], "New Orleans", "LA", [-90.0715, 29.9511], 530, 8, 3.08, [[-88.7037, 32.3643], [-89.2903, 31.3271], [-90.1848, 30.4458]]),
  route("charlotte-savannah", "Southeast", "Charlotte", "NC", [-80.8431, 35.2271], "Savannah", "GA", [-81.0998, 32.0809], 255, 4, 3.05, [[-80.8987, 34.0007], [-81.0348, 33.4918], [-81.0348, 32.4316]]),
  route("chicago-houston", "Central", "Chicago", "IL", [-87.6298, 41.8781], "Houston", "TX", [-95.3698, 29.7604], 1080, 16, 3.06, [[-89.6501, 39.7817], [-90.1994, 38.627], [-92.2896, 34.7465], [-94.1574, 31.6035]]),
  route("denver-chicago", "Central", "Denver", "CO", [-104.9903, 39.7392], "Chicago", "IL", [-87.6298, 41.8781], 1000, 14.5, 3.18, [[-101.7222, 41.1403], [-96.7026, 40.8136], [-93.6091, 41.6005], [-90.1994, 38.627]]),
  route("minneapolis-chicago", "Midwest", "Minneapolis", "MN", [-93.265, 44.9778], "Chicago", "IL", [-87.6298, 41.8781], 410, 6.5, 3.17, [[-91.4985, 44.8113], [-89.4012, 43.0731], [-88.0133, 42.0451]]),
  route("detroit-nashville", "Midwest", "Detroit", "MI", [-83.0458, 42.3314], "Nashville", "TN", [-86.7816, 36.1627], 535, 8, 3.11, [[-84.512, 39.1031], [-85.7585, 38.2527], [-86.1581, 39.7684]]),
  route("cleveland-chicago", "Midwest", "Cleveland", "OH", [-81.6944, 41.4993], "Chicago", "IL", [-87.6298, 41.8781], 345, 5.5, 3.14, [[-83.5552, 41.6528], [-85.1394, 41.0793], [-86.252, 41.6764]]),
  route("austin-dallas", "Texas", "Austin", "TX", [-97.7431, 30.2672], "Dallas", "TX", [-96.797, 32.7767], 195, 3, 2.98, [[-97.1467, 31.5493], [-97.3208, 32.3513]]),
  route("dallas-denver", "Mountain West", "Dallas", "TX", [-96.797, 32.7767], "Denver", "CO", [-104.9903, 39.7392], 795, 12, 3.04, [[-101.8313, 35.222], [-104.6091, 38.2544]]),
  route("houston-new-orleans", "Gulf Coast", "Houston", "TX", [-95.3698, 29.7604], "New Orleans", "LA", [-90.0715, 29.9511], 350, 5.5, 2.96, [[-93.2174, 30.2266], [-92.0198, 30.2241], [-91.1546, 30.4515]]),
  route("san-antonio-houston", "Texas", "San Antonio", "TX", [-98.4936, 29.4241], "Houston", "TX", [-95.3698, 29.7604], 200, 3, 2.95, [[-97.9414, 29.5016], [-96.8761, 29.9055]]),
  route("san-francisco-los-angeles", "West Coast", "San Francisco", "CA", [-122.4194, 37.7749], "Los Angeles", "CA", [-118.2437, 34.0522], 385, 6.5, 4.02, [[-121.8947, 37.3394], [-121.6555, 36.6777], [-120.6596, 35.2828], [-119.0187, 35.3733]]),
  route("los-angeles-las-vegas", "Southwest", "Los Angeles", "CA", [-118.2437, 34.0522], "Las Vegas", "NV", [-115.1398, 36.1699], 270, 4.5, 3.91, [[-117.2898, 34.1083], [-116.9114, 34.8481], [-115.543, 35.913]]),
  route("phoenix-las-vegas", "Southwest", "Phoenix", "AZ", [-112.074, 33.4484], "Las Vegas", "NV", [-115.1398, 36.1699], 300, 4.75, 3.58, [[-112.5838, 33.8753], [-113.9938, 35.1894], [-114.053, 35.1983]]),
  route("san-diego-phoenix", "Southwest", "San Diego", "CA", [-117.1611, 32.7157], "Phoenix", "AZ", [-112.074, 33.4484], 355, 5.5, 3.72, [[-115.5631, 32.9787], [-114.6277, 32.6927], [-113.9536, 33.0478]]),
  route("salt-lake-denver", "Mountain West", "Salt Lake City", "UT", [-111.891, 40.7608], "Denver", "CO", [-104.9903, 39.7392], 520, 8, 3.36, [[-109.5498, 38.5733], [-108.5506, 39.0639], [-106.8317, 39.1911]]),
  route("denver-yellowstone", "Mountain West", "Denver", "CO", [-104.9903, 39.7392], "Yellowstone", "WY", [-110.5885, 44.428], 510, 8.5, 3.31, [[-105.5911, 41.3114], [-108.5506, 41.5869], [-110.7624, 43.4799]]),
  route("portland-seattle", "Pacific Northwest", "Portland", "OR", [-122.6765, 45.5152], "Seattle", "WA", [-122.3321, 47.6062], 175, 3, 3.69, [[-122.9382, 46.1382], [-122.9007, 46.7298], [-122.4443, 47.2529]]),
  route("seattle-san-francisco", "West Coast", "Seattle", "WA", [-122.3321, 47.6062], "San Francisco", "CA", [-122.4194, 37.7749], 810, 12.5, 3.76, [[-122.6765, 45.5152], [-123.0351, 44.9429], [-122.8756, 42.3265], [-122.3917, 40.5865]]),
  route("los-angeles-seattle", "West Coast", "Los Angeles", "CA", [-118.2437, 34.0522], "Seattle", "WA", [-122.3321, 47.6062], 1140, 17.5, 3.84, [[-119.0187, 35.3733], [-121.2908, 37.9577], [-122.4194, 37.7749], [-122.3917, 40.5865], [-122.6765, 45.5152]]),
];

validateDemoDefinitions();

export const demoRouteOptions: DemoRouteOption[] = demoDefinitions.map(
  (definition) => ({
    id: definition.id,
    label: `${definition.start.name}, ${definition.start.state} → ${definition.finish.name}, ${definition.finish.state}`,
    region: definition.region,
    distanceMiles: definition.distanceMiles,
    durationHours: definition.durationHours,
  }),
);

export function getDemoRoutePlan(id: string): RoutePlan | null {
  const definition = demoDefinitions.find((candidate) => candidate.id === id);
  return definition ? buildDemoPlan(definition) : null;
}

function route(
  id: string,
  region: string,
  startName: string,
  startState: string,
  startCoordinate: Coordinate,
  finishName: string,
  finishState: string,
  finishCoordinate: Coordinate,
  distanceMiles: number,
  durationHours: number,
  basePrice: number,
  waypoints: Coordinate[],
): DemoRouteDefinition {
  return {
    id,
    region,
    start: { name: startName, state: startState, coordinate: startCoordinate },
    finish: {
      name: finishName,
      state: finishState,
      coordinate: finishCoordinate,
    },
    distanceMiles,
    durationHours,
    basePrice,
    waypoints,
  };
}

function buildDemoPlan(definition: DemoRouteDefinition): RoutePlan {
  const coordinates = [
    definition.start.coordinate,
    ...definition.waypoints,
    definition.finish.coordinate,
  ];
  const stopCount = Math.max(0, Math.ceil(definition.distanceMiles / 430) - 1);
  const stops = Array.from({ length: stopCount }, (_, index) =>
    buildStop(definition, coordinates, index, stopCount),
  );
  const totalGallons = definition.distanceMiles / 10;
  const totalCost = stops.reduce(
    (sum, stop) => sum + stop.cost_usd,
    Math.min(50, totalGallons) * definition.basePrice,
  );

  return {
    start: locationPayload(definition.start),
    finish: locationPayload(definition.finish),
    route: {
      distance_miles: definition.distanceMiles,
      duration_hours: definition.durationHours,
      geojson: {
        type: "FeatureCollection",
        features: [
          {
            type: "Feature",
            geometry: { type: "LineString", coordinates },
            properties: {
              kind: "route",
              distance_miles: definition.distanceMiles,
            },
          },
        ],
      },
    },
    vehicle: {
      maximum_range_miles: 500,
      fuel_economy_mpg: 10,
      tank_capacity_gallons: 50,
    },
    fuel_plan: {
      initial_fuel_estimate: {
        gallons: round(Math.min(50, totalGallons)),
        cost_usd: round(Math.min(50, totalGallons) * definition.basePrice),
        price_reference: {
          opis_id: `demo-${definition.id}-origin`,
          name: `${definition.start.name} Demo Fuel`,
          city: definition.start.name,
          state: definition.start.state,
          price_per_gallon_usd: definition.basePrice,
        },
      },
      stops,
      total_gallons: round(totalGallons),
      total_cost_usd: round(totalCost),
      currency: "USD",
    },
    metadata: {
      external_calls: "None. This route is bundled with the frontend.",
      routing_provider: "Bundled demo snapshot",
      geocoding_provider: "Bundled city coordinates",
      station_coordinate_accuracy: "Illustrative demo locations",
      route_alternatives_evaluated: 1,
      feasible_route_alternatives: 1,
      selection_score_usd: round(totalCost),
      selection_policy: "Illustrative frontend-only demo.",
      assumption:
        "Demo geometry and fuel stops are representative and do not replace a live route plan.",
      demo: true,
    },
  };
}

function buildStop(
  definition: DemoRouteDefinition,
  coordinates: Coordinate[],
  index: number,
  stopCount: number,
): FuelStop {
  const sequence = index + 1;
  const progress = sequence / (stopCount + 1);
  const coordinate = interpolatePolyline(coordinates, progress);
  const routeMile = definition.distanceMiles * progress;
  const totalGallons = definition.distanceMiles / 10;
  const initialGallons = Math.min(50, totalGallons);
  const gallons =
    stopCount > 0 ? Math.min(50, (totalGallons - initialGallons) / stopCount) : 0;
  const price = round(definition.basePrice + ((index % 3) - 1) * 0.09);

  return {
    sequence,
    opis_id: `demo-${definition.id}-${sequence}`,
    name: `FuelUp Demo Stop ${sequence}`,
    address: "Representative route location",
    city: `Route stop ${sequence}`,
    state: "US",
    latitude: coordinate[1],
    longitude: coordinate[0],
    route_mile: round(routeMile),
    distance_to_route_miles: 0,
    price_per_gallon_usd: price,
    fuel_on_arrival_gallons: round(5 + (index % 3) * 2.5),
    gallons: round(gallons),
    cost_usd: round(gallons * price),
  };
}

function locationPayload(location: DemoRouteDefinition["start"]) {
  return {
    query: `${location.name}, ${location.state}`,
    display_name: `${location.name}, ${location.state}, United States`,
    latitude: location.coordinate[1],
    longitude: location.coordinate[0],
  };
}

function interpolatePolyline(
  coordinates: Coordinate[],
  progress: number,
): Coordinate {
  const segmentPosition = progress * (coordinates.length - 1);
  const segmentIndex = Math.min(
    coordinates.length - 2,
    Math.floor(segmentPosition),
  );
  const fraction = segmentPosition - segmentIndex;
  const start = coordinates[segmentIndex];
  const finish = coordinates[segmentIndex + 1];
  return [
    start[0] + (finish[0] - start[0]) * fraction,
    start[1] + (finish[1] - start[1]) * fraction,
  ];
}

function round(value: number) {
  return Math.round(value * 100) / 100;
}

function validateDemoDefinitions() {
  if (demoDefinitions.length !== 25) {
    throw new Error("The bundled demo catalog must contain exactly 25 routes.");
  }
  const identifiers = new Set(demoDefinitions.map((route) => route.id));
  if (identifiers.size !== demoDefinitions.length) {
    throw new Error("Bundled demo route identifiers must be unique.");
  }
  for (const definition of demoDefinitions) {
    if (
      definition.distanceMiles <= 0 ||
      definition.durationHours <= 0 ||
      definition.waypoints.length === 0
    ) {
      throw new Error(`Invalid bundled demo route: ${definition.id}`);
    }
  }
}
