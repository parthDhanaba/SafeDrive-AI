import React from 'react';
import { Eye, Smile, Brain, Activity } from 'lucide-react';

export default function TelemetryGauges({ telemetry, config }) {
  const ear = telemetry?.ear ?? 0.0;
  const mar = telemetry?.mar ?? 0.0;
  const earThreshold = config?.ear_threshold ?? 0.22;
  const marThreshold = config?.mar_threshold ?? 0.50;

  const eyeProb = telemetry?.eye_open_prob;
  const yawnProb = telemetry?.yawn_prob;
  const eyeThreshold = config?.eye_model_threshold ?? 0.50;
  const yawnThreshold = config?.yawn_model_threshold ?? 0.40;

  const closedFrames = telemetry?.closed_frames ?? 0;
  const yawns = telemetry?.yawns ?? 0;

  // Visual gauge percentages
  const earPercent = Math.min(100, Math.max(0, (ear / 0.40) * 100));
  const marPercent = Math.min(100, Math.max(0, (mar / 0.80) * 100));
  const earThresholdPercent = (earThreshold / 0.40) * 100;
  const marThresholdPercent = (marThreshold / 0.80) * 100;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
      {/* 1. Eye Aspect Ratio (EAR) */}
      <div className="glass-panel" style={{ padding: '1.15rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.6rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Eye size={18} color="#00F0FF" />
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)' }}>Eye Aspect Ratio (EAR)</span>
          </div>
          <span className="mono-num" style={{
            fontSize: '1.25rem',
            fontWeight: 700,
            color: ear < earThreshold ? '#EF4444' : '#10B981'
          }}>
            {ear.toFixed(3)}
          </span>
        </div>

        {/* Progress Bar with Threshold Pin */}
        <div style={{ position: 'relative', width: '100%', height: '8px', background: 'rgba(255, 255, 255, 0.08)', borderRadius: '4px', overflow: 'hidden', marginBottom: '0.5rem' }}>
          <div style={{
            width: `${earPercent}%`,
            height: '100%',
            background: ear < earThreshold ? '#EF4444' : '#00F0FF',
            borderRadius: '4px',
            transition: 'width 0.15s ease'
          }} />
          {/* Threshold marker */}
          <div style={{
            position: 'absolute',
            left: `${earThresholdPercent}%`,
            top: 0,
            bottom: 0,
            width: '2px',
            backgroundColor: '#F59E0B'
          }} />
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
          <span>Limit: {earThreshold}</span>
          <span>Frames: {closedFrames} / 45</span>
        </div>
      </div>

      {/* 2. Mouth Aspect Ratio (MAR) */}
      <div className="glass-panel" style={{ padding: '1.15rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.6rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Smile size={18} color="#F59E0B" />
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)' }}>Mouth Aspect Ratio (MAR)</span>
          </div>
          <span className="mono-num" style={{
            fontSize: '1.25rem',
            fontWeight: 700,
            color: mar >= marThreshold ? '#EF4444' : '#E2E8F0'
          }}>
            {mar.toFixed(3)}
          </span>
        </div>

        <div style={{ position: 'relative', width: '100%', height: '8px', background: 'rgba(255, 255, 255, 0.08)', borderRadius: '4px', overflow: 'hidden', marginBottom: '0.5rem' }}>
          <div style={{
            width: `${marPercent}%`,
            height: '100%',
            background: mar >= marThreshold ? '#EF4444' : '#F59E0B',
            borderRadius: '4px',
            transition: 'width 0.15s ease'
          }} />
          <div style={{
            position: 'absolute',
            left: `${marThresholdPercent}%`,
            top: 0,
            bottom: 0,
            width: '2px',
            backgroundColor: '#EF4444'
          }} />
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
          <span>Limit: {marThreshold}</span>
          <span>Yawns: {yawns} / 3</span>
        </div>
      </div>

      {/* 3. Eye AI Model Probability */}
      <div className="glass-panel" style={{ padding: '1.15rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.6rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Brain size={18} color="#A855F7" />
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)' }}>Eye AI (Open Prob)</span>
          </div>
          <span className="mono-num" style={{
            fontSize: '1.25rem',
            fontWeight: 700,
            color: eyeProb !== null && eyeProb < eyeThreshold ? '#EF4444' : '#10B981'
          }}>
            {eyeProb !== null ? `${(eyeProb * 100).toFixed(1)}%` : 'N/A'}
          </span>
        </div>

        <div style={{ position: 'relative', width: '100%', height: '8px', background: 'rgba(255, 255, 255, 0.08)', borderRadius: '4px', overflow: 'hidden', marginBottom: '0.5rem' }}>
          <div style={{
            width: eyeProb !== null ? `${eyeProb * 100}%` : '0%',
            height: '100%',
            background: eyeProb !== null && eyeProb < eyeThreshold ? '#EF4444' : 'linear-gradient(90deg, #6366F1, #A855F7)',
            borderRadius: '4px',
            transition: 'width 0.2s ease'
          }} />
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
          <span>Model: 64x64 Keras</span>
          <span>Class: {eyeProb !== null && eyeProb < eyeThreshold ? 'CLOSED (0)' : 'OPEN (1)'}</span>
        </div>
      </div>

      {/* 4. Yawn AI Model Probability */}
      <div className="glass-panel" style={{ padding: '1.15rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.6rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Activity size={18} color="#EC4899" />
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)' }}>Yawn AI (Yawn Prob)</span>
          </div>
          <span className="mono-num" style={{
            fontSize: '1.25rem',
            fontWeight: 700,
            color: yawnProb !== null && yawnProb >= yawnThreshold ? '#EF4444' : '#E2E8F0'
          }}>
            {yawnProb !== null ? `${(yawnProb * 100).toFixed(1)}%` : 'N/A'}
          </span>
        </div>

        <div style={{ position: 'relative', width: '100%', height: '8px', background: 'rgba(255, 255, 255, 0.08)', borderRadius: '4px', overflow: 'hidden', marginBottom: '0.5rem' }}>
          <div style={{
            width: yawnProb !== null ? `${yawnProb * 100}%` : '0%',
            height: '100%',
            background: yawnProb !== null && yawnProb >= yawnThreshold ? '#EF4444' : 'linear-gradient(90deg, #EC4899, #F43F5E)',
            borderRadius: '4px',
            transition: 'width 0.2s ease'
          }} />
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
          <span>Model: 128x128 MobileNet</span>
          <span>Threshold: {yawnThreshold}</span>
        </div>
      </div>
    </div>
  );
}
