import React from 'react';
import { CheckCircle2, AlertTriangle, AlertOctagon, BellRing, RotateCcw, EyeOff, UserX } from 'lucide-react';

export default function StatusBanner({ telemetry, alarm, onReset }) {
  const isDrowsy = telemetry?.drowsy;
  const isEyeClosed = telemetry?.state === 'CLOSED';
  const isNoFace = telemetry?.state === 'NO FACE';
  const isCountdown = alarm?.countdown_active;
  const remaining = alarm?.remaining_time ?? 10;
  const isEmergency = alarm?.is_emergency;
  const isAlarmPlaying = alarm?.is_playing;
  const dangerReason = alarm?.danger_reason;

  // Browser Web Audio companion alarm
  React.useEffect(() => {
    let audioCtx = null;
    let osc = null;
    let gain = null;
    let timer = null;

    if (isAlarmPlaying || isCountdown || isEmergency) {
      try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (AudioCtx) {
          audioCtx = new AudioCtx();
          osc = audioCtx.createOscillator();
          gain = audioCtx.createGain();

          osc.type = isEmergency ? 'sawtooth' : 'sine';
          osc.frequency.setValueAtTime(isEmergency ? 880 : 750, audioCtx.currentTime);

          gain.gain.setValueAtTime(0.12, audioCtx.currentTime);
          osc.connect(gain);
          gain.connect(audioCtx.destination);
          osc.start();

          let high = true;
          timer = setInterval(() => {
            if (audioCtx && osc && audioCtx.state === 'running') {
              const freq = high ? (isEmergency ? 960 : 850) : (isEmergency ? 720 : 650);
              osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
              high = !high;
            }
          }, 250);
        }
      } catch (e) {
        // Harmless if browser blocks prior to user gesture
      }
    }

    return () => {
      if (timer) clearInterval(timer);
      if (osc) {
        try { osc.stop(); osc.disconnect(); } catch (e) {}
      }
      if (audioCtx) {
        try { audioCtx.close(); } catch (e) {}
      }
    };
  }, [isAlarmPlaying, isCountdown, isEmergency]);

  // Determine Primary Visual Theme
  let statusTheme = {
    title: 'ATTENTIVE & SAFE',
    subtitle: 'Eye gaze and facial attentiveness metrics within nominal limits',
    color: '#10B981',
    bg: 'rgba(16, 185, 129, 0.1)',
    border: 'rgba(16, 185, 129, 0.3)',
    icon: <CheckCircle2 size={32} color="#10B981" />
  };

  if (isEmergency) {
    statusTheme = {
      title: 'CRITICAL EMERGENCY — SOS ACTIVATED',
      subtitle: dangerReason || 'Driver failed to acknowledge danger countdown',
      color: '#EF4444',
      bg: 'rgba(239, 68, 68, 0.2)',
      border: '#EF4444',
      icon: <AlertOctagon size={32} color="#EF4444" />
    };
  } else if (isCountdown) {
    statusTheme = {
      title: `WARNING: RESPONSE REQUIRED (${remaining}s)`,
      subtitle: dangerReason || 'Driver fatigue detected — please press Reset or tap key R',
      color: '#F59E0B',
      bg: 'rgba(245, 158, 11, 0.18)',
      border: 'rgba(245, 158, 11, 0.5)',
      icon: <BellRing size={32} color="#F59E0B" />
    };
  } else if (isDrowsy || isEyeClosed) {
    statusTheme = {
      title: 'DROWSINESS DETECTED',
      subtitle: `Sustained eye closure (${telemetry?.closed_frames || 0} frames) detected by AI`,
      color: '#EF4444',
      bg: 'rgba(239, 68, 68, 0.15)',
      border: 'rgba(239, 68, 68, 0.4)',
      icon: <EyeOff size={32} color="#EF4444" />
    };
  } else if (telemetry?.yawn_active || telemetry?.state === 'YAWNING') {
    statusTheme = {
      title: 'YAWN EVENT IN PROGRESS',
      subtitle: `Mouth separation sustained above threshold (Yawns: ${telemetry?.yawns || 0})`,
      color: '#F97316',
      bg: 'rgba(249, 115, 22, 0.15)',
      border: 'rgba(249, 115, 22, 0.4)',
      icon: <AlertTriangle size={32} color="#F97316" />
    };
  } else if (isNoFace) {
    statusTheme = {
      title: 'NO DRIVER FACE DETECTED',
      subtitle: 'Cabin scanning active — please position driver facing camera',
      color: '#94A3B8',
      bg: 'rgba(148, 163, 184, 0.08)',
      border: 'rgba(148, 163, 184, 0.2)',
      icon: <UserX size={32} color="#94A3B8" />
    };
  }

  return (
    <div
      className={`glass-panel ${isCountdown || isEmergency ? 'strobe-alert' : ''}`}
      style={{
        padding: '1.25rem 1.5rem',
        background: statusTheme.bg,
        borderColor: statusTheme.border,
        display: 'flex',
        flexDirection: 'column',
        gap: '0.85rem',
        boxShadow: (isCountdown || isEmergency) ? 'var(--shadow-glow-danger)' : 'none'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{
            width: '48px',
            height: '48px',
            borderRadius: '12px',
            background: 'rgba(0, 0, 0, 0.3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: `1px solid ${statusTheme.border}`
          }}>
            {statusTheme.icon}
          </div>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: statusTheme.color, letterSpacing: '-0.01em' }}>
              {statusTheme.title}
            </h2>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              {statusTheme.subtitle}
            </p>
          </div>
        </div>

        {/* Reset / Acknowledge Button */}
        {(isCountdown || isEmergency || isAlarmPlaying) && (
          <button
            onClick={onReset}
            style={{
              padding: '0.65rem 1.4rem',
              borderRadius: 'var(--radius-md)',
              background: '#EF4444',
              color: '#FFF',
              fontWeight: 700,
              fontSize: '0.875rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              boxShadow: '0 0 20px rgba(239, 68, 68, 0.5)',
              transform: 'scale(1.02)'
            }}
          >
            <RotateCcw size={16} />
            <span>ACKNOWLEDGE / RESET (R)</span>
          </button>
        )}
      </div>

      {/* Countdown Progress Bar */}
      {isCountdown && (
        <div style={{ width: '100%', marginTop: '0.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: '#FBBF24', marginBottom: '0.35rem' }}>
            <span>DRIVER RESPONSE COUNTDOWN</span>
            <span>{remaining} SECONDS BEFORE SOS DISPATCH</span>
          </div>
          <div style={{ width: '100%', height: '8px', background: 'rgba(0, 0, 0, 0.4)', borderRadius: '4px', overflow: 'hidden' }}>
            <div
              style={{
                width: `${(remaining / 10) * 100}%`,
                height: '100%',
                background: 'linear-gradient(90deg, #EF4444, #F59E0B)',
                transition: 'width 1s linear'
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
