"use client";

import { useEffect, useMemo } from "react";
import L from "leaflet";
import {
  CircleMarker,
  MapContainer,
  Marker,
  Popup,
  Polyline,
  TileLayer,
  useMap,
} from "react-leaflet";
import { formatCurrency, formatNumber } from "@/lib/format";
import type { Position, RoutePlan } from "@/lib/types";

function MapBounds({ positions }: { positions: Position[] }) {
  const map = useMap();

  useEffect(() => {
    if (positions.length > 1) {
      map.fitBounds(L.latLngBounds(positions), { padding: [36, 36] });
    }
  }, [map, positions]);

  return null;
}

function MapViewportControls({ positions }: { positions: Position[] }) {
  const map = useMap();

  function fitRoute() {
    if (positions.length > 1) {
      map.fitBounds(L.latLngBounds(positions), { padding: [36, 36] });
    }
  }

  return (
    <button className="fit-route-button" type="button" onClick={fitRoute}>
      Fit route
    </button>
  );
}

function SelectedStopFocus({
  plan,
  selectedStop,
}: {
  plan: RoutePlan;
  selectedStop: number | null;
}) {
  const map = useMap();

  useEffect(() => {
    if (selectedStop === null) {
      return;
    }
    const stop = plan.fuel_plan.stops.find(
      (candidate) => candidate.sequence === selectedStop,
    );
    if (stop) {
      map.flyTo([stop.latitude, stop.longitude], 9, { duration: 0.8 });
    }
  }, [map, plan, selectedStop]);

  return null;
}

function stopIcon(sequence: number) {
  return L.divIcon({
    className: "fuel-stop-marker",
    html: `<span>${sequence}</span>`,
    iconSize: [34, 34],
    iconAnchor: [17, 17],
    popupAnchor: [0, -18],
  });
}

export function RouteMap({
  plan,
  selectedStop,
}: {
  plan: RoutePlan;
  selectedStop: number | null;
}) {
  const routePositions = useMemo<Position[]>(() => {
    const routeFeature = plan.route.geojson.features.find(
      (feature) => feature.properties.kind === "route",
    );
    if (!routeFeature || routeFeature.geometry.type !== "LineString") {
      return [];
    }
    return (routeFeature.geometry.coordinates as number[][]).map(
      ([longitude, latitude]) => [latitude, longitude],
    );
  }, [plan]);

  const boundsPositions = useMemo(
    () => [
      ...routePositions,
      ...plan.fuel_plan.stops.map(
        (stop) => [stop.latitude, stop.longitude] as Position,
      ),
    ],
    [plan, routePositions],
  );

  const fallbackCenter: Position = [
    plan.start.latitude,
    plan.start.longitude,
  ];

  return (
    <MapContainer
      center={fallbackCenter}
      zoom={5}
      className="route-map"
      scrollWheelZoom
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <Polyline
        positions={routePositions}
        pathOptions={{
          color: "#102a43",
          weight: 10,
          opacity: 0.5,
          lineCap: "round",
          lineJoin: "round",
        }}
      />
      <Polyline
        positions={routePositions}
        pathOptions={{
          color: "#2563eb",
          weight: 6,
          opacity: 1,
          lineCap: "round",
          lineJoin: "round",
        }}
      />
      <CircleMarker
        center={[plan.start.latitude, plan.start.longitude]}
        radius={8}
        pathOptions={{
          color: "#ffffff",
          fillColor: "#17352f",
          fillOpacity: 1,
          weight: 3,
        }}
      >
        <Popup>
          <strong>Start</strong>
          <br />
          {plan.start.display_name}
        </Popup>
      </CircleMarker>
      <CircleMarker
        center={[plan.finish.latitude, plan.finish.longitude]}
        radius={8}
        pathOptions={{
          color: "#ffffff",
          fillColor: "#f15a29",
          fillOpacity: 1,
          weight: 3,
        }}
      >
        <Popup>
          <strong>Finish</strong>
          <br />
          {plan.finish.display_name}
        </Popup>
      </CircleMarker>
      {plan.fuel_plan.stops.map((stop) => (
        <Marker
          key={`${stop.opis_id}-${stop.sequence}`}
          position={[stop.latitude, stop.longitude]}
          icon={stopIcon(stop.sequence)}
        >
          <Popup>
            <div className="map-popup">
              <strong>{stop.name}</strong>
              <span>
                {stop.city}, {stop.state}
              </span>
              <span>
                {formatCurrency(stop.price_per_gallon_usd)}/gal ·{" "}
                {formatNumber(stop.gallons)} gal
              </span>
            </div>
          </Popup>
        </Marker>
      ))}
      <MapBounds positions={boundsPositions} />
      <MapViewportControls positions={boundsPositions} />
      <SelectedStopFocus plan={plan} selectedStop={selectedStop} />
    </MapContainer>
  );
}
