'use client';

import { useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

const TILES = 'http://localhost:3000';            // Martin tile server
const WS_URL = 'ws://localhost:8000/ws/vehicles'; // live vehicle feed

const SUBWAY_COLORS: maplibregl.ExpressionSpecification = [
  'match', ['get', 'route_id'],
  'Red', '#DA291C',
  'Orange', '#ED8B00',
  'Blue', '#003DA5',
  'Green-B', '#00843D', 'Green-C', '#00843D', 'Green-D', '#00843D', 'Green-E', '#00843D',
  '#888888',
];

export default function LiveMap() {
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!container.current) return;
    const map = new maplibregl.Map({
      container: container.current,
      style: 'https://demotiles.maplibre.org/style.json',
      center: [-71.0589, 42.3601],
      zoom: 11,
    });

    let ws: WebSocket | null = null;

    map.on('load', () => {
      // Real MBTA network from Martin vector tiles, beneath the dots.
      map.addSource('routes', { type: 'vector', url: `${TILES}/route_shapes` });
      map.addLayer({
        id: 'routes', type: 'line', source: 'routes', 'source-layer': 'route_shapes',
        paint: { 'line-color': ['get', 'route_color'], 'line-width': 2, 'line-opacity': 0.85 },
      });
      map.addSource('stops', { type: 'vector', url: `${TILES}/stops` });
      map.addLayer({
        id: 'stops', type: 'circle', source: 'stops', 'source-layer': 'stops', minzoom: 13,
        paint: {
          'circle-radius': 3, 'circle-color': '#ffffff',
          'circle-stroke-color': '#333333', 'circle-stroke-width': 1,
        },
      });

      // Live vehicles.
      map.addSource('vehicles', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
      map.addLayer({
        id: 'vehicles', type: 'circle', source: 'vehicles',
        paint: {
          'circle-radius': 5, 'circle-stroke-width': 1, 'circle-stroke-color': '#ffffff',
          'circle-color': SUBWAY_COLORS,
        },
      });

      ws = new WebSocket(WS_URL);
      ws.onmessage = (e) => {
        const { vehicles } = JSON.parse(e.data);
        const src = map.getSource('vehicles') as maplibregl.GeoJSONSource | undefined;
        src?.setData({
          type: 'FeatureCollection',
          features: vehicles.map((v: { lon: number; lat: number; route_id: string; vehicle_id: string }) => ({
            type: 'Feature',
            geometry: { type: 'Point', coordinates: [v.lon, v.lat] },
            properties: { route_id: v.route_id, vehicle_id: v.vehicle_id },
          })),
        });
      };
    });

    return () => {
      ws?.close();
      map.remove();
    };
  }, []);

  return <div ref={container} style={{ position: 'absolute', inset: 0 }} />;
}
