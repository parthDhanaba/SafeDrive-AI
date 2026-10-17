import React from 'react';
import { Cpu, CheckCircle2, AlertCircle, Layers, FileCheck } from 'lucide-react';

export default function ModelStatus({ models }) {
  const eyeModel = models?.eye_model;
  const yawnModel = models?.yawn_model;

  return (
    <div className="glass-panel" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Cpu size={18} color="#00F0FF" />
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-main)', textTransform: 'uppercase' }}>
            Deep Learning AI Inference Models
          </h3>
        </div>
        <span style={{ fontSize: '0.72rem', color: '#10B981', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
          PYTORCH BACKEND ACTIVE
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.85rem' }}>
        {/* Eye Model Card */}
        <div style={{
          padding: '0.85rem',
          borderRadius: 'var(--radius-md)',
          background: 'rgba(255, 255, 255, 0.03)',
          border: `1px solid ${eyeModel?.loaded ? 'rgba(16, 185, 129, 0.25)' : 'rgba(239, 68, 68, 0.25)'}`,
          display: 'flex',
          flexDirection: 'column',
          gap: '0.5rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#F1F5F9' }}>
              Eye Drowsiness Model
            </span>
            <span className={`badge ${eyeModel?.loaded ? 'badge-normal' : 'badge-danger'}`}>
              {eyeModel?.loaded ? <CheckCircle2 size={12} /> : <AlertCircle size={12} />}
              {eyeModel?.loaded ? 'LOADED' : 'OFFLINE'}
            </span>
          </div>

          <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
            <div>File: <span style={{ color: 'var(--text-muted)' }}>eye_drowsiness_model.keras</span></div>
            <div>Architecture: <span style={{ color: 'var(--text-muted)' }}>Conv2D (64x64x3) + Sigmoid</span></div>
            <div>Class 0: <span style={{ color: '#F87171' }}>Closed Eyes (&lt; {eyeModel?.threshold || 0.50})</span></div>
            <div>Class 1: <span style={{ color: '#34D399' }}>Open Eyes (&gt;= {eyeModel?.threshold || 0.50})</span></div>
          </div>
        </div>

        {/* Yawn Model Card */}
        <div style={{
          padding: '0.85rem',
          borderRadius: 'var(--radius-md)',
          background: 'rgba(255, 255, 255, 0.03)',
          border: `1px solid ${yawnModel?.loaded ? 'rgba(16, 185, 129, 0.25)' : 'rgba(239, 68, 68, 0.25)'}`,
          display: 'flex',
          flexDirection: 'column',
          gap: '0.5rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#F1F5F9' }}>
              Yawn Detection Model
            </span>
            <span className={`badge ${yawnModel?.loaded ? 'badge-normal' : 'badge-danger'}`}>
              {yawnModel?.loaded ? <CheckCircle2 size={12} /> : <AlertCircle size={12} />}
              {yawnModel?.loaded ? 'LOADED' : 'OFFLINE'}
            </span>
          </div>

          <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
            <div>File: <span style={{ color: 'var(--text-muted)' }}>yawn_model.keras</span></div>
            <div>Architecture: <span style={{ color: 'var(--text-muted)' }}>MobileNetV2 (128x128x3)</span></div>
            <div>Class 0: <span style={{ color: '#34D399' }}>No Yawn (&lt; {yawnModel?.threshold || 0.40})</span></div>
            <div>Class 1: <span style={{ color: '#F97316' }}>Yawn (&gt;= {yawnModel?.threshold || 0.40})</span></div>
          </div>
        </div>
      </div>
    </div>
  );
}
