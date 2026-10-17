import React from 'react';
import { ShieldAlert, Video, Radio, Cpu, Activity, AlertTriangle } from 'lucide-react';

export default function Navbar({ systemStatus, isOnline, pingMs }) {
  const cameraOk = systemStatus?.camera_connected;
  const eyeModelOk = systemStatus?.models?.eye_model?.loaded;
  const yawnModelOk = systemStatus?.models?.yawn_model?.loaded;
  const isEmergency = systemStatus?.alarm?.is_emergency;

  return (
    <header className="glass-panel" style={{ padding: '0.85rem 1.5rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
      {/* Brand Identity */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div style={{
          width: '42px',
          height: '42px',
          borderRadius: '10px',
          background: 'linear-gradient(135deg, rgba(0, 240, 255, 0.2), rgba(99, 102, 241, 0.2))',
          border: '1px solid var(--accent-cyan)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: 'var(--shadow-glow-cyan)'
        }}>
          <ShieldAlert size={24} color="#00F0FF" />
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <h1 style={{ fontSize: '1.25rem', fontWeight: 700, letterSpacing: '-0.02em', background: 'linear-gradient(to right, #FFF, #94A3B8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              SafeDrive AI
            </h1>
            <span style={{ fontSize: '0.65rem', padding: '0.15rem 0.5rem', borderRadius: '4px', background: 'rgba(56, 189, 248, 0.1)', border: '1px solid rgba(56, 189, 248, 0.2)', color: '#38BDF8', fontFamily: 'var(--font-mono)' }}>
              v1.0.0
            </span>
          </div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Autonomous Driver Attentiveness & AI Fatigue Telemetry
          </p>
        </div>
      </div>

      {/* Connectivity & Subsystem Health Badges */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem', flexWrap: 'wrap' }}>
        {/* Backend Status */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.45rem',
          padding: '0.35rem 0.75rem',
          borderRadius: '9999px',
          fontSize: '0.75rem',
          fontFamily: 'var(--font-mono)',
          fontWeight: 600,
          background: isOnline ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
          border: `1px solid ${isOnline ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
          color: isOnline ? '#34D399' : '#F87171'
        }}>
          <span style={{
            width: '7px',
            height: '7px',
            borderRadius: '50%',
            backgroundColor: isOnline ? '#34D399' : '#F87171',
            boxShadow: isOnline ? '0 0 8px #34D399' : '0 0 8px #F87171'
          }} />
          {isOnline ? `FLASK API ONLINE (${pingMs}ms)` : 'FLASK DISCONNECTED'}
        </div>

        {/* Camera Sensor Status */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.45rem',
          padding: '0.35rem 0.75rem',
          borderRadius: '9999px',
          fontSize: '0.75rem',
          fontFamily: 'var(--font-mono)',
          fontWeight: 600,
          background: cameraOk ? 'rgba(0, 240, 255, 0.1)' : 'rgba(245, 158, 11, 0.1)',
          border: `1px solid ${cameraOk ? 'rgba(0, 240, 255, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`,
          color: cameraOk ? '#00F0FF' : '#FBBF24'
        }}>
          <Video size={13} />
          {cameraOk ? 'WEBCAM 640x480' : 'TEST STREAM / OFFLINE'}
        </div>

        {/* Deep Learning Core Status */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.45rem',
          padding: '0.35rem 0.75rem',
          borderRadius: '9999px',
          fontSize: '0.75rem',
          fontFamily: 'var(--font-mono)',
          fontWeight: 600,
          background: (eyeModelOk && yawnModelOk) ? 'rgba(139, 92, 246, 0.15)' : 'rgba(245, 158, 11, 0.15)',
          border: `1px solid ${(eyeModelOk && yawnModelOk) ? 'rgba(139, 92, 246, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`,
          color: (eyeModelOk && yawnModelOk) ? '#C084FC' : '#FBBF24'
        }}>
          <Cpu size={13} />
          {(eyeModelOk && yawnModelOk) ? '2 AI MODELS ACTIVE' : 'HYBRID CV FALLBACK'}
        </div>

        {isEmergency && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            padding: '0.35rem 0.85rem',
            borderRadius: '9999px',
            fontSize: '0.75rem',
            fontWeight: 700,
            fontFamily: 'var(--font-mono)',
            background: 'rgba(239, 68, 68, 0.25)',
            border: '1px solid #EF4444',
            color: '#FCA5A5',
            animation: 'pulse-danger 1s infinite'
          }}>
            <AlertTriangle size={14} color="#EF4444" />
            SOS ACTIVATED
          </div>
        )}
      </div>
    </header>
  );
}
