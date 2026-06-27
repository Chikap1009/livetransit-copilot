'use client';

import { useEffect, useState } from 'react';

const INCIDENTS_URL = 'http://localhost:8000/incidents?limit=8';
const POLL_MS = 30000;

type Incident = {
  id: number;
  kind: string;
  route_id: string | null;
  severity: string;
  summary: string;
  created_at: string;
};

const SEV_COLOR: Record<string, string> = {
  high: '#ef4444',
  medium: '#f59e0b',
  low: '#22c55e',
};

export default function IncidentsPanel() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [open, setOpen] = useState(true);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const res = await fetch(INCIDENTS_URL);
        const data = await res.json();
        if (alive) setIncidents(data.incidents ?? []);
      } catch {
        /* ignore transient fetch errors */
      }
    };
    load();
    const id = setInterval(load, POLL_MS);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  return (
    <div
      style={{
        position: 'absolute', bottom: 16, left: 10, zIndex: 2, width: 320, maxWidth: '40vw',
        background: 'rgba(11,11,22,0.92)', color: '#e5e7eb', borderRadius: 10,
        font: '13px system-ui, sans-serif', boxShadow: '0 6px 24px rgba(0,0,0,0.4)',
        overflow: 'hidden', border: '1px solid rgba(255,255,255,0.08)',
      }}
    >
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          width: '100%', display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer',
          background: 'transparent', border: 'none', color: '#fff', padding: '10px 12px',
          font: '600 13px system-ui', textAlign: 'left',
        }}
      >
        <span style={{ fontSize: 15 }}>🛰️</span>
        Network Watchdog
        <span style={{ marginLeft: 'auto', opacity: 0.6, fontWeight: 400 }}>
          {incidents.length} incident{incidents.length === 1 ? '' : 's'} {open ? '▾' : '▸'}
        </span>
      </button>
      {open && (
        <div style={{ maxHeight: 260, overflowY: 'auto' }}>
          {incidents.length === 0 && (
            <div style={{ padding: '10px 12px', opacity: 0.6 }}>No incidents reported.</div>
          )}
          {incidents.map((i) => (
            <div
              key={i.id}
              style={{ padding: '9px 12px', borderTop: '1px solid rgba(255,255,255,0.06)' }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 3 }}>
                <span style={{
                  width: 8, height: 8, borderRadius: '50%',
                  background: SEV_COLOR[i.severity] ?? '#9ca3af',
                }} />
                <span style={{ fontWeight: 600, textTransform: 'capitalize' }}>{i.kind}</span>
                {i.route_id && (
                  <span style={{
                    background: 'rgba(255,255,255,0.1)', borderRadius: 5, padding: '1px 6px',
                    fontSize: 11,
                  }}>{i.route_id}</span>
                )}
                <span style={{ marginLeft: 'auto', fontSize: 11, opacity: 0.5 }}>
                  {new Date(i.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
              <div style={{ opacity: 0.85, lineHeight: 1.35 }}>{i.summary}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
