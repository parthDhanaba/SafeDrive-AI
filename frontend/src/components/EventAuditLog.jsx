import React, { useState, useEffect } from 'react';
import { History, RefreshCw, AlertCircle, ShieldAlert, FileText } from 'lucide-react';

export default function EventAuditLog({ isOnline }) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchEvents = async () => {
    if (!isOnline) return;
    setLoading(true);
    try {
      const res = await fetch('/api/events?limit=15');
      if (res.ok) {
        const data = await res.json();
        setEvents(data.events || []);
      }
    } catch (e) {
      console.error('Failed to load events:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents();
    const interval = setInterval(fetchEvents, 5000);
    return () => clearInterval(interval);
  }, [isOnline]);

  return (
    <div className="glass-panel" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <History size={18} color="#00F0FF" />
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-main)', textTransform: 'uppercase' }}>
            Safety Incident Audit Log (SQLite DB)
          </h3>
        </div>
        <button
          onClick={fetchEvents}
          disabled={loading}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.35rem',
            padding: '0.3rem 0.65rem',
            borderRadius: 'var(--radius-sm)',
            background: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid var(--border-subtle)',
            color: 'var(--text-muted)',
            fontSize: '0.72rem'
          }}
        >
          <RefreshCw size={12} className={loading ? 'spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {events.length === 0 ? (
        <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-dim)', fontSize: '0.85rem' }}>
          No safety incidents recorded in this session. Driver attentiveness nominal.
        </div>
      ) : (
        <div style={{ overflowX: 'auto', maxHeight: '280px', overflowY: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.75rem', textAlign: 'left', fontFamily: 'var(--font-mono)' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-dim)' }}>
                <th style={{ padding: '0.5rem 0.6rem' }}>TIME</th>
                <th style={{ padding: '0.5rem 0.6rem' }}>EVENT</th>
                <th style={{ padding: '0.5rem 0.6rem' }}>SEVERITY</th>
                <th style={{ padding: '0.5rem 0.6rem' }}>EAR / MAR</th>
                <th style={{ padding: '0.5rem 0.6rem' }}>STATUS</th>
              </tr>
            </thead>
            <tbody>
              {events.map((evt) => {
                const isEmerg = evt.event_type === 'EMERGENCY';
                const isDrowsy = evt.event_type === 'DROWSINESS';
                const isYawn = evt.event_type.includes('YAWN');

                let badgeClass = 'badge-normal';
                if (isEmerg) badgeClass = 'badge-danger';
                else if (isDrowsy) badgeClass = 'badge-danger';
                else if (isYawn) badgeClass = 'badge-warning';

                const timeFormatted = evt.timestamp ? evt.timestamp.split('T')[1]?.substring(0, 8) || evt.timestamp : '—';

                return (
                  <tr key={evt.id} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.03)' }}>
                    <td style={{ padding: '0.55rem 0.6rem', color: 'var(--text-muted)' }}>{timeFormatted}</td>
                    <td style={{ padding: '0.55rem 0.6rem', fontWeight: 600, color: 'var(--text-main)' }}>
                      {evt.event_type}
                    </td>
                    <td style={{ padding: '0.55rem 0.6rem' }}>
                      <span className={`badge ${badgeClass}`} style={{ fontSize: '0.65rem', padding: '0.15rem 0.5rem' }}>
                        {evt.severity}
                      </span>
                    </td>
                    <td style={{ padding: '0.55rem 0.6rem', color: 'var(--text-dim)' }}>
                      {evt.ear_value !== null ? evt.ear_value.toFixed(2) : '—'} / {evt.mar_value !== null ? evt.mar_value.toFixed(2) : '—'}
                    </td>
                    <td style={{ padding: '0.55rem 0.6rem', color: evt.response_status === 'ALARM' ? '#F87171' : 'var(--text-muted)' }}>
                      {evt.response_status}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
