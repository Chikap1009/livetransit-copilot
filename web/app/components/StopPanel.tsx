'use client';

import { useEffect, useState } from 'react';

const API = 'http://localhost:8000';

type Arrival = {
  route_id: string;
  scheduled: string;
  predicted_eta: string | null;
  predicted_delay_s: number | null;
};
type ArrivalsResponse = {
  arrivals: Arrival[];
  accuracy: { mae_model_s: number | null; mae_schedule_s: number | null };
};

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('en-US', {
    hour: '2-digit', minute: '2-digit', timeZone: 'America/New_York',
  });
}

function delay(d: number | null): { text: string; color: string } {
  if (d == null) return { text: '—', color: '#777' };
  const m = Math.max(1, Math.round(Math.abs(d) / 60));
  if (d > 30) return { text: `${m}m late`, color: '#c0392b' };
  if (d < -30) return { text: `${m}m early`, color: '#2563eb' };
  return { text: 'on time', color: '#1a7f37' };
}

export default function StopPanel({
  stop,
  onClose,
}: {
  stop: { id: string; name: string };
  onClose: () => void;
}) {
  const [data, setData] = useState<ArrivalsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setData(null);
    fetch(`${API}/stops/${encodeURIComponent(stop.id)}/arrivals`)
      .then((r) => r.json())
      .then((d) => { if (alive) setData(d); })
      .catch(() => { if (alive) setData(null); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [stop.id]);

  return (
    <div
      style={{
        position: 'absolute', top: 58, left: 10, zIndex: 4, width: 300, maxHeight: '70vh',
        overflow: 'auto', background: '#fff', color: '#111', borderRadius: 10,
        boxShadow: '0 6px 24px rgba(0,0,0,0.32)', font: '13px system-ui, sans-serif',
      }}
    >
      <div
        style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          background: '#1a1a2e', color: '#fff', padding: '10px 14px', fontWeight: 600,
          position: 'sticky', top: 0,
        }}
      >
        <span>{stop.name}</span>
        <span onClick={onClose} style={{ cursor: 'pointer', fontSize: 18, lineHeight: 1 }}>×</span>
      </div>

      {loading && <div style={{ padding: 14, color: '#555' }}>Loading predictions…</div>}

      {!loading && (!data || data.arrivals.length === 0) && (
        <div style={{ padding: 14, color: '#555' }}>No predicted arrivals right now.</div>
      )}

      {!loading && data && data.arrivals.map((a, i) => {
        const d = delay(a.predicted_delay_s);
        return (
          <div
            key={i}
            style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '10px 14px', borderTop: '1px solid #eee',
            }}
          >
            <span style={{ fontWeight: 700, fontSize: 15 }}>{a.route_id}</span>
            <span style={{ textAlign: 'right', lineHeight: 1.35 }}>
              {fmtTime(a.predicted_eta ?? a.scheduled)}
              <br />
              <span style={{ color: d.color, fontWeight: 600 }}>{d.text}</span>
            </span>
          </div>
        );
      })}

      {!loading && data && (
        <div style={{ padding: '9px 14px', background: '#f6f7fb', color: '#555', fontSize: 11 }}>
          Predicted by a LightGBM model · MAE <b>{data.accuracy?.mae_model_s ?? '—'}s</b> vs
          schedule baseline {data.accuracy?.mae_schedule_s ?? '—'}s
        </div>
      )}
    </div>
  );
}
