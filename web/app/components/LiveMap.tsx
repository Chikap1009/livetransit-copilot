'use client';

import { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

const TILES = 'http://localhost:3000';            // Martin tile server
const API = 'http://localhost:8000';              // FastAPI
const WS_URL = 'ws://localhost:8000/ws/vehicles'; // live vehicle feed

function delayLabel(d: number | null): string {
  if (d == null) return '?';
  const m = Math.max(1, Math.round(Math.abs(d) / 60));
  if (d > 30) return `${m}m late`;
  if (d < -30) return `${m}m early`;
  return 'on time';
}

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
  const [connected, setConnected] = useState(false);
  const [count, setCount] = useState<number | null>(null);

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

      // Click a vehicle dot -> popup with route + id.
      map.on('click', 'vehicles', (e) => {
        const p = e.features?.[0]?.properties as { route_id: string; vehicle_id: string } | undefined;
        if (!p) return;
        new maplibregl.Popup()
          .setLngLat(e.lngLat)
          .setHTML(`<b>${p.route_id}</b><br>vehicle ${p.vehicle_id}`)
          .addTo(map);
      });

      // Click a stop -> popup with predicted arrivals from the ML model.
      map.on('click', 'stops', async (e) => {
        const p = e.features?.[0]?.properties as { stop_id: string; stop_name?: string } | undefined;
        if (!p) return;
        const title = p.stop_name ?? 'Stop';
        const popup = new maplibregl.Popup()
          .setLngLat(e.lngLat)
          .setHTML(`<b>${title}</b><br>loading…`)
          .addTo(map);
        try {
          const res = await fetch(`${API}/stops/${encodeURIComponent(p.stop_id)}/arrivals`);
          const data: { arrivals: { route: string; predicted_delay_s: number | null }[] } = await res.json();
          const rows = data.arrivals.map((a) => `${a.route} — ${delayLabel(a.predicted_delay_s)}`).join('<br>')
            || 'No predicted arrivals right now.';
          popup.setHTML(`<b>${title}</b><br>${rows}`);
        } catch {
          popup.setHTML(`<b>${title}</b><br>(could not load predictions)`);
        }
      });

      for (const layer of ['vehicles', 'stops']) {
        map.on('mouseenter', layer, () => { map.getCanvas().style.cursor = 'pointer'; });
        map.on('mouseleave', layer, () => { map.getCanvas().style.cursor = ''; });
      }

      ws = new WebSocket(WS_URL);
      ws.onopen = () => setConnected(true);
      ws.onclose = () => setConnected(false);
      ws.onmessage = (e) => {
        const { vehicles } = JSON.parse(e.data);
        setCount(vehicles.length);
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

  return (
    <>
      <div
        style={{
          position: 'absolute', top: 10, left: 10, zIndex: 1,
          background: 'rgba(0,0,0,0.75)', color: '#fff', padding: '8px 12px',
          borderRadius: 6, font: '14px system-ui, sans-serif',
        }}
      >
        <span style={{ color: connected ? '#3f3' : '#f33' }}>●</span>{' '}
        {connected ? `live — ${count ?? 0} vehicles` : 'connecting…'}
      </div>
      <div ref={container} style={{ position: 'absolute', inset: 0 }} />
    </>
  );
}
