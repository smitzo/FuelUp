import type { Metadata } from "next";
import "leaflet/dist/leaflet.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "FuelUp India Route Planner",
  description:
    "Plan Indian road trips with vehicle-aware petrol and diesel stops, transparent price freshness, and costs in rupees per litre.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en-IN">
      <body>{children}</body>
    </html>
  );
}
