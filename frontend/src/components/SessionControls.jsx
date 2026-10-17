import React from 'react';
import { Play, Pause, RotateCcw, Clock, Shield, AlertTriangle, Siren } from 'lucide-react';

export default function SessionControls({ monitoringActive, onStart, onStop, onReset, sessionData, alarm }) {
  const uptime = sessionData?.uptime_seconds ?? 0;
  const hours = Math.floor(uptime / 3600);
  const minutes = Math.floor((uptime % 3600) / 60);
  const seconds = uptime % 60;
  const durationStr = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;

  const yawns = sessionData?.total_yawns ?? 0;
  const isAlarmPlaying = alarm?.is_playing;
  const isEmergency = alarm?.is_emergency;

  return (
    <div className="glass-panel" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-main)', textTransform: 'uppercase' }}>
          Monitoring Session Controls
        </h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          <Clock size={14} color="#00F0FF" />
          <span>SESSION: {durationStr}</span>
        </div>
      </div>

      {/* Control Buttons */}
      <div style={{ display: 'flex', gap: '0.65rem', flexWrap: 'wrap' }}>
        {monitoringActive ? (
          <button
            onClick={onStop}
            style={{
              flex: 1,
              padding: '0.65rem 1rem',
              borderRadius: 'var(--radius-sm)',
              background: 'rgba(245, 158, 11, 0.15)',
              border: '1px solid rgba(245, 158, 11, 0.4)',
              color: '#FBBF24',
              fontWeight: 600,
              fontSize: '0.85rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.45rem'
            }}
          >
            <Pause size={15} />
            <span>PAUSE MONITORING</span>
          </button>
        ) : (
          <button
            onClick={onStart}
            style={{
              flex: 1,
              padding: '0.65rem 1rem',
              borderRadius: 'var(--radius-sm)',
              background: 'rgba(16, 185, 129, 0.15)',
              border: '1px solid rgba(16, 185, 129, 0.4)',
              color: '#34D399',
              fontWeight: 600,
              fontSize: '0.85rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.45rem'
            }}
          >
            <Play size={15} />
            <span>START MONITORING</span>
          </button>
        )}

        <button
          onClick={onReset}
          style={{
            padding: '0.65rem 1.25rem',
            borderRadius: 'var(--radius-sm)',
            background: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid var(--border-medium)',
            color: 'var(--text-main)',
            fontWeight: 600,
            fontSize: '0.85rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.45rem'
          }}
        >
          <RotateCcw size={15} />
          <span>RESET (R)</span>
        </button>
      </div>

      {/* Metrics Summary Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.65rem' }}>
        <div style={{ padding: '0.65rem', background: 'rgba(0, 0, 0, 0.25)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', textAlign: 'center' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginBottom: '0.2rem' }}>SESSION YAWNS</div>
          <div className="mono-num" style={{ fontSize: '1.25rem', fontWeight: 700, color: yawns >= 3 ? '#EF4444' : '#F59E0B' }}>
            {yawns}
          </div>
        </div>

        <div style={{ padding: '0.65rem', background: 'rgba(0, 0, 0, 0.25)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', textAlign: 'center' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginBottom: '0.2rem' }}>AUDIO ALARM</div>
          <div className="mono-num" style={{ fontSize: '1rem', fontWeight: 700, color: isAlarmPlaying ? '#EF4444' : '#10B981', paddingTop: '0.2rem' }}>
            {isAlarmPlaying ? 'ACTIVE' : 'IDLE'}
          </div>
        </div>

        <div style={{ padding: '0.65rem', background: 'rgba(0, 0, 0, 0.25)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', textAlign: 'center' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginBottom: '0.2rem' }}>SOS SYSTEM</div>
          <div className="mono-num" style={{ fontSize: '1rem', fontWeight: 700, color: isEmergency ? '#EF4444' : '#38BDF8', paddingTop: '0.2rem' }}>
            {isEmergency ? 'DISPATCHED' : 'ARMED'}
          </div>
        </div>
      </div>
    </div>
  );
}
