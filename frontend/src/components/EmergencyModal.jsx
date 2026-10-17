import React from 'react';
import { AlertOctagon, MapPin, MessageSquare, Camera, RotateCcw, ExternalLink } from 'lucide-react';

export default function EmergencyModal({ alarm, location, sessionData, onReset }) {
  if (!alarm?.is_emergency) return null;

  const photoPath = sessionData?.last_photo_path;
  const photoName = photoPath ? photoPath.split(/[\\/]/).pop() : null;
  const photoUrl = photoName ? `/emergency_captures/${photoName}` : null;
  const mapsUrl = location?.maps_url;
  const whatsappStatus = sessionData?.last_whatsapp_status || 'SIMULATED';

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      backgroundColor: 'rgba(5, 7, 13, 0.88)',
      backdropFilter: 'blur(12px)',
      zIndex: 1000,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '1.5rem'
    }}>
      <div className="glass-panel strobe-alert" style={{
        maxWidth: '560px',
        width: '100%',
        padding: '2rem',
        borderRadius: 'var(--radius-xl)',
        border: '2px solid #EF4444',
        boxShadow: 'var(--shadow-glow-danger)',
        display: 'flex',
        flexDirection: 'column',
        gap: '1.25rem'
      }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{
            width: '54px',
            height: '54px',
            borderRadius: '14px',
            background: 'rgba(239, 68, 68, 0.25)',
            border: '2px solid #EF4444',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <AlertOctagon size={32} color="#EF4444" />
          </div>
          <div>
            <h2 style={{ fontSize: '1.35rem', fontWeight: 800, color: '#F87171' }}>
              EMERGENCY SOS ACTIVATED
            </h2>
            <p style={{ fontSize: '0.85rem', color: '#CBD5E1' }}>
              Driver unresponsive to fatigue alarm. Autonomous safety protocols executed.
            </p>
          </div>
        </div>

        {/* SOS Details Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '0.85rem', background: 'rgba(0, 0, 0, 0.35)', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
          {/* Location */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              <MapPin size={16} color="#00F0FF" />
              <span>GPS Fix:</span>
            </div>
            {location?.available && location?.latitude ? (
              <a
                href={mapsUrl}
                target="_blank"
                rel="noreferrer"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                  color: '#00F0FF',
                  fontSize: '0.85rem',
                  fontFamily: 'var(--font-mono)',
                  textDecoration: 'none'
                }}
              >
                <span>{location.latitude.toFixed(4)}, {location.longitude.toFixed(4)}</span>
                <ExternalLink size={13} />
              </a>
            ) : (
              <span style={{ fontSize: '0.85rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                {location?.status_text || 'GPS Acquiring...'}
              </span>
            )}
          </div>

          {/* WhatsApp Alert */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              <MessageSquare size={16} color="#10B981" />
              <span>Family WhatsApp:</span>
            </div>
            <span className="badge badge-normal" style={{ fontSize: '0.72rem' }}>
              {whatsappStatus}
            </span>
          </div>

          {/* Photo Snapshot */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              <Camera size={16} color="#A855F7" />
              <span>Emergency Photo:</span>
            </div>
            <span style={{ fontSize: '0.8rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
              {photoName || 'Captured to emergency_captures/'}
            </span>
          </div>
        </div>

        {/* Clear / Dismiss Button */}
        <button
          onClick={onReset}
          style={{
            padding: '0.85rem',
            borderRadius: 'var(--radius-md)',
            background: 'linear-gradient(135deg, #10B981, #059669)',
            color: '#FFF',
            fontWeight: 700,
            fontSize: '0.95rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.5rem',
            boxShadow: '0 4px 15px rgba(16, 185, 129, 0.4)'
          }}
        >
          <RotateCcw size={18} />
          <span>I AM ATTENTIVE — CLEAR SOS & RESET SYSTEM</span>
        </button>
      </div>
    </div>
  );
}
