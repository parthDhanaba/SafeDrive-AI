import React, { useState, useRef, useEffect } from 'react';
import { Camera, Maximize2, Minimize2, RefreshCw, AlertCircle, ShieldCheck } from 'lucide-react';

export default function VideoFeed({ isOnline, telemetry, cameraConnected, cameraError }) {
  const [streamError, setStreamError] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [streamKey, setStreamKey] = useState(Date.now());
  const containerRef = useRef(null);

  // Re-attempt stream connection when backend comes back online
  useEffect(() => {
    if (isOnline) {
      setStreamError(false);
      setStreamKey(Date.now());
    }
  }, [isOnline]);

  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().catch(err => console.error(err));
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  const handleReloadStream = () => {
    setStreamError(false);
    setStreamKey(Date.now());
  };

  const streamUrl = `/api/video_feed?t=${streamKey}`;

  return (
    <div className="glass-panel hud-corners" ref={containerRef} style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      {/* Panel Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <div style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: streamError ? '#EF4444' : (cameraConnected ? '#10B981' : '#F59E0B'),
            boxShadow: streamError ? '0 0 10px #EF4444' : '0 0 10px #10B981'
          }} />
          <h2 style={{ fontSize: '1rem', fontWeight: 600, letterSpacing: '0.01em', textTransform: 'uppercase', color: 'var(--text-main)' }}>
            Live Cabin Vision & Biometric Telemetry
          </h2>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <button
            onClick={handleReloadStream}
            title="Reconnect video stream"
            style={{
              padding: '0.4rem 0.6rem',
              borderRadius: 'var(--radius-sm)',
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-muted)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
              fontSize: '0.75rem'
            }}
          >
            <RefreshCw size={13} />
            <span>Reload</span>
          </button>

          <button
            onClick={toggleFullscreen}
            title="Toggle Fullscreen"
            style={{
              padding: '0.4rem 0.6rem',
              borderRadius: 'var(--radius-sm)',
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-muted)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
              fontSize: '0.75rem'
            }}
          >
            {isFullscreen ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
          </button>
        </div>
      </div>

      {/* Video Stream Container */}
      <div className="video-wrapper">
        {isOnline && !streamError ? (
          <img
            key={streamKey}
            src={streamUrl}
            alt="SafeDrive AI Live Stream"
            className="video-stream"
            onError={() => setStreamError(true)}
          />
        ) : (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '1rem',
            padding: '2rem',
            textAlign: 'center',
            background: 'rgba(10, 15, 26, 0.95)',
            width: '100%',
            height: '100%'
          }}>
            <div style={{
              width: '56px',
              height: '56px',
              borderRadius: '50%',
              background: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <AlertCircle size={28} color="#EF4444" />
            </div>
            <div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#F87171', marginBottom: '0.35rem' }}>
                {!isOnline ? 'Flask Backend Not Reachable' : 'No Video Signal from Flask Stream'}
              </h3>
              <p style={{ fontSize: '0.825rem', color: 'var(--text-muted)', maxWidth: '420px', lineHeight: 1.5 }}>
                {!isOnline
                  ? 'Ensure python backend is running on http://127.0.0.1:5000 via "py server.py".'
                  : (cameraError || 'Webcam could not be opened or stream was interrupted. Check camera permissions and click Reconnect.')}
              </p>
            </div>
            <button
              onClick={handleReloadStream}
              style={{
                padding: '0.5rem 1.25rem',
                borderRadius: 'var(--radius-sm)',
                background: 'rgba(0, 240, 255, 0.15)',
                border: '1px solid var(--accent-cyan)',
                color: '#00F0FF',
                fontSize: '0.85rem',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem'
              }}
            >
              <RefreshCw size={14} />
              Retry Connection
            </button>
          </div>
        )}

        {/* Live HUD Watermark / Overlays */}
        <div style={{
          position: 'absolute',
          bottom: '12px',
          left: '12px',
          display: 'flex',
          alignItems: 'center',
          gap: '0.6rem',
          pointerEvents: 'none'
        }}>
          <div style={{
            background: 'rgba(0, 0, 0, 0.65)',
            backdropFilter: 'blur(8px)',
            border: '1px solid rgba(255, 255, 255, 0.15)',
            padding: '0.2rem 0.6rem',
            borderRadius: '4px',
            fontSize: '0.7rem',
            fontFamily: 'var(--font-mono)',
            color: '#E2E8F0',
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem'
          }}>
            <span style={{ color: '#00F0FF' }}>●</span>
            <span>FPS: {telemetry?.fps ? Math.round(telemetry.fps) : 30}</span>
          </div>

          <div style={{
            background: 'rgba(0, 0, 0, 0.65)',
            backdropFilter: 'blur(8px)',
            border: '1px solid rgba(255, 255, 255, 0.15)',
            padding: '0.2rem 0.6rem',
            borderRadius: '4px',
            fontSize: '0.7rem',
            fontFamily: 'var(--font-mono)',
            color: '#A7F3D0'
          }}>
            DRIVER: {telemetry?.state === 'NO FACE' ? 'UNLOCKED' : 'LOCKED'}
          </div>
        </div>
      </div>
    </div>
  );
}
