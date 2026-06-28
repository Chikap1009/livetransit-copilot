'use client';

import { useCopilotAction } from '@copilotkit/react-core';
import { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

import StopPanel from './StopPanel';
import { TILES_BASE, WS_URL } from '../config';

const NO_ROUTE = '__none__';

type TripLeg = {
  route: string;
  fromLat: number; fromLon: number; fromLabel: string;
  toLat: number; toLon: number; toLabel: string;
};

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
  const mapRef = useRef<maplibregl.Map | null>(null);
  const pinsRef = useRef<maplibregl.Marker[]>([]);
  const [connected, setConnected] = useState(false);
  const [count, setCount] = useState<number | null>(null);
  const [selectedStop, setSelectedStop] = useState<{ id: string; name: string } | null>(null);

  useEffect(() => {
    if (!container.current) return;
    const map = new maplibregl.Map({
      container: container.current,
      style: 'https://demotiles.maplibre.org/style.json',
      center: [-71.0589, 42.3601],
      zoom: 11,
    });
    mapRef.current = map;

    let ws: WebSocket | null = null;

    map.on('load', () => {
      // Real MBTA network from Martin vector tiles, beneath the dots.
      map.addSource('routes', { type: 'vector', tiles: [`${TILES_BASE}/route_shapes/{z}/{x}/{y}`], maxzoom: 16 });
      map.addLayer({
        id: 'routes', type: 'line', source: 'routes', 'source-layer': 'route_shapes',
        paint: { 'line-color': ['get', 'route_color'], 'line-width': 2, 'line-opacity': 0.85 },
      });
      // Agent-controlled highlight: a dark casing + bright cyan "neon" core, drawn
      // above the routes (both start matching nothing). On highlight we also dim the
      // base routes so the chosen one pops.
      map.addLayer({
        id: 'route-highlight-casing', type: 'line', source: 'routes', 'source-layer': 'route_shapes',
        filter: ['==', ['get', 'route_id'], NO_ROUTE],
        paint: { 'line-color': '#0b0b16', 'line-width': 10, 'line-opacity': 0.95 },
      });
      map.addLayer({
        id: 'route-highlight', type: 'line', source: 'routes', 'source-layer': 'route_shapes',
        filter: ['==', ['get', 'route_id'], NO_ROUTE],
        paint: { 'line-color': '#18ffff', 'line-width': 4, 'line-opacity': 1, 'line-blur': 1 },
      });
      map.addSource('stops', { type: 'vector', tiles: [`${TILES_BASE}/stops/{z}/{x}/{y}`], maxzoom: 16 });
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

      // Click a vehicle dot -> small readable popup (inline styles beat any global CSS).
      map.on('click', 'vehicles', (e) => {
        const p = e.features?.[0]?.properties as { route_id: string; vehicle_id: string } | undefined;
        if (!p) return;
        new maplibregl.Popup({ closeButton: false, offset: 12 })
          .setLngLat(e.lngLat)
          .setHTML(
            `<div style="font:13px system-ui,sans-serif;color:#111">` +
            `<b style="font-size:14px">${p.route_id}</b><br>vehicle ${p.vehicle_id}</div>`,
          )
          .addTo(map);
      });

      // Click a stop -> open the rich React prediction panel.
      map.on('click', 'stops', (e) => {
        const p = e.features?.[0]?.properties as { stop_id: string; stop_name?: string } | undefined;
        if (p) setSelectedStop({ id: p.stop_id, name: p.stop_name ?? 'Stop' });
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
      pinsRef.current.forEach((m) => m.remove());
      pinsRef.current = [];
      mapRef.current = null;
      map.remove();
    };
  }, []);

  // --- Map-fusion actions the agent can call (CopilotKit forwards them as tools) ---
  useCopilotAction({
    name: 'highlightRoute',
    description:
      'Highlight a single MBTA route line on the map. Call this whenever the user asks to ' +
      'show, highlight, or point out a route. The route id is like Red, Orange, Blue, Green-B, ' +
      '1, or 66.',
    parameters: [{ name: 'route', type: 'string', description: 'MBTA route id', required: true }],
    // Handlers return a string result so CopilotKit can pair the tool call with a
    // result (a void return leaves a dangling tool call that breaks chat history).
    handler: ({ route }: { route: string }): string => {
      const map = mapRef.current;
      if (!map?.getLayer('route-highlight')) return 'Map not ready.';
      const f: maplibregl.FilterSpecification = ['==', ['get', 'route_id'], route];
      map.setFilter('route-highlight-casing', f);
      map.setFilter('route-highlight', f);
      map.setPaintProperty('routes', 'line-opacity', 0.12);   // fade the rest
      return `Highlighted route ${route} on the map.`;
    },
  });

  useCopilotAction({
    name: 'dropPin',
    description: 'Drop a labeled pin at a latitude/longitude and fly the map there.',
    parameters: [
      { name: 'lat', type: 'number', description: 'latitude', required: true },
      { name: 'lon', type: 'number', description: 'longitude', required: true },
      { name: 'label', type: 'string', description: 'short label', required: false },
    ],
    handler: ({ lat, lon, label }: { lat: number; lon: number; label?: string }): string => {
      const map = mapRef.current;
      if (!map) return 'Map not ready.';
      const marker = new maplibregl.Marker({ color: '#1a73e8' }).setLngLat([lon, lat]);
      if (label) {
        marker.setPopup(
          new maplibregl.Popup({ offset: 24 }).setHTML(
            `<div style="font:13px system-ui;color:#111">${label}</div>`,
          ),
        );
      }
      marker.addTo(map);
      pinsRef.current.push(marker);
      map.flyTo({ center: [lon, lat], zoom: 14 });
      return `Dropped a pin${label ? ` labeled "${label}"` : ''}.`;
    },
  });

  useCopilotAction({
    name: 'drawTrip',
    description:
      'Draw a planned trip on the map: highlight every leg\'s route line and drop a green pin at ' +
      'the start, amber pins at any transfer points, and a red pin at the destination. Pass the ' +
      '`draw` array returned by the plan_trip tool as `legs`.',
    parameters: [
      {
        name: 'legs',
        type: 'object[]',
        description: 'Ordered trip legs.',
        required: true,
        attributes: [
          { name: 'route', type: 'string', description: 'MBTA route id for this leg' },
          { name: 'fromLat', type: 'number', description: 'board latitude' },
          { name: 'fromLon', type: 'number', description: 'board longitude' },
          { name: 'fromLabel', type: 'string', description: 'board stop name' },
          { name: 'toLat', type: 'number', description: 'alight latitude' },
          { name: 'toLon', type: 'number', description: 'alight longitude' },
          { name: 'toLabel', type: 'string', description: 'alight stop name' },
        ],
      },
    ],
    handler: ({ legs }: { legs: TripLeg[] }): string => {
      const map = mapRef.current;
      if (!map?.getLayer('route-highlight') || !legs?.length) return 'Nothing to draw.';

      // Highlight every route used by the trip, fade the rest.
      const routes = [...new Set(legs.map((l) => l.route))];
      const f: maplibregl.FilterSpecification = ['in', ['get', 'route_id'], ['literal', routes]];
      map.setFilter('route-highlight-casing', f);
      map.setFilter('route-highlight', f);
      map.setPaintProperty('routes', 'line-opacity', 0.12);

      // Pins: green start, amber transfers, red destination. Clear any old ones first.
      pinsRef.current.forEach((m) => m.remove());
      pinsRef.current = [];
      const bounds = new maplibregl.LngLatBounds();
      const addPin = (lat: number, lon: number, label: string, color: string) => {
        const marker = new maplibregl.Marker({ color })
          .setLngLat([lon, lat])
          .setPopup(
            new maplibregl.Popup({ offset: 24 }).setHTML(
              `<div style="font:13px system-ui;color:#111">${label}</div>`,
            ),
          )
          .addTo(map);
        pinsRef.current.push(marker);
        bounds.extend([lon, lat]);
      };
      addPin(legs[0].fromLat, legs[0].fromLon, `Start: ${legs[0].fromLabel}`, '#16a34a');
      legs.forEach((l, i) => {
        const last = i === legs.length - 1;
        addPin(
          l.toLat, l.toLon,
          last ? `Destination: ${l.toLabel}` : `Transfer to ${legs[i + 1].route} at ${l.toLabel}`,
          last ? '#dc2626' : '#f59e0b',
        );
      });
      map.fitBounds(bounds, { padding: 80, maxZoom: 14, duration: 800 });
      return `Drew a ${legs.length}-leg trip on the map.`;
    },
  });

  useCopilotAction({
    name: 'clearMap',
    description: 'Remove all agent highlights and pins from the map.',
    // A no-parameter action makes some models emit non-object args (CopilotKit then
    // errors), so we declare one harmless optional param. The handler ignores it.
    parameters: [
      { name: 'reason', type: 'string', description: 'optional, ignored', required: false },
    ],
    handler: (): string => {
      const map = mapRef.current;
      if (map?.getLayer('route-highlight')) {
        const none: maplibregl.FilterSpecification = ['==', ['get', 'route_id'], NO_ROUTE];
        map.setFilter('route-highlight-casing', none);
        map.setFilter('route-highlight', none);
        map.setPaintProperty('routes', 'line-opacity', 0.85);   // un-dim
      }
      pinsRef.current.forEach((m) => m.remove());
      pinsRef.current = [];
      return 'Cleared the map.';
    },
  });

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
      {selectedStop && (
        <StopPanel stop={selectedStop} onClose={() => setSelectedStop(null)} />
      )}
      <div ref={container} style={{ position: 'absolute', inset: 0 }} />
    </>
  );
}
