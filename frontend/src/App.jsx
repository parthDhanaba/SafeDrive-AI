import React, { useState, useEffect, useCallback } from 'react';
import Navbar from './components/Navbar';
import StatusBanner from './components/StatusBanner';
import VideoFeed from './components/VideoFeed';
import TelemetryGauges from './components/TelemetryGauges';
import ModelStatus from './components/ModelStatus';
import SessionControls from './components/SessionControls';
import EventAuditLog from './components/EventAuditLog';
import EmergencyModal from './components/EmergencyModal';
import DemoDrawer from './components/DemoDrawer';

export default function App() {
  const [systemStatus, setSystemStatus] = useState(null);
  const [isOnline, setIsOnline] = useState(false);
  const [pingMs, setPingMs] = useState(0);
  const [config, setConfig] = useState(null);

  // Fetch live system status
  const fetchStatus = useCallback(async () => {
    const t0 = performance.now();
    try {
      const res = await fetch('/api/status');
      const roundTrip = Math.round(performance.now() - t0);
      if (res.ok) {
        const data = await res.json();
        setSystemStatus(data);
        setIsOnline(true);
        setPingMs(roundTrip);
      } else {
        setIsOnline(false);
      }
    } catch (e) {
      setIsOnline(false);
    }
  }, []);

  // Fetch initial config
  const fetchConfig = useCallback(async () => {
    try {
      const res = await fetch('/api/config');
      if (res.ok) {
        const data = await res.json();
        setConfig(data);
      }
    } catch (e) {
      console.error('Failed to load config:', e);
    }
  }, []);

  // Polling loop
  useEffect(() => {
    fetchStatus();
    fetchConfig();
    const interval = setInterval(fetchStatus, 350);
    return () => clearInterval(interval);
  }, [fetchStatus, fetchConfig]);

  // Global 'R' key listener for instant driver reset
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'r' || e.key === 'R') {
        handleReset();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleStart = async () => {
    try {
      await fetch('/api/session/start', { method: 'POST' });
      fetchStatus();
    } catch (e) {
      console.error(e);
    }
  };

  const handleStop = async () => {
    try {
      await fetch('/api/session/stop', { method: 'POST' });
      fetchStatus();
    } catch (e) {
      console.error(e);
    }
  };

  const handleReset = async () => {
    try {
      await fetch('/api/session/reset', { method: 'POST' });
      fetchStatus();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="dashboard-container">
      {/* 1. Header Navigation Bar */}
      <Navbar systemStatus={systemStatus} isOnline={isOnline} pingMs={pingMs} />

      {/* 2. Primary Attentiveness & Warning Banner */}
      <StatusBanner
        telemetry={systemStatus?.telemetry}
        alarm={systemStatus?.alarm}
        onReset={handleReset}
      />

      {/* 3. Main Dashboard Responsive Grid */}
      <div className="dashboard-grid">
        {/* Left Primary Column: Camera Feed & Biometric Telemetry */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* Live Video Feed */}
          <VideoFeed
            isOnline={isOnline}
            telemetry={systemStatus?.telemetry}
            cameraConnected={systemStatus?.camera_connected}
            cameraError={systemStatus?.camera_error}
          />

          {/* Real-time EAR, MAR & Deep Learning Gauges */}
          <TelemetryGauges
            telemetry={systemStatus?.telemetry}
            config={config}
          />

          {/* Deep Learning Models Health & Specifications */}
          <ModelStatus models={systemStatus?.models} />

          {/* Academic Presentation Demo Drawer */}
          <DemoDrawer onReset={handleReset} />
        </div>

        {/* Right Sidebar Column: Session Controls & SQLite Event Audit Log */}
        <div className="sidebar-column">
          {/* Session Monitoring Controls */}
          <SessionControls
            monitoringActive={systemStatus?.monitoring_active}
            onStart={handleStart}
            onStop={handleStop}
            onReset={handleReset}
            sessionData={systemStatus?.session}
            alarm={systemStatus?.alarm}
          />

          {/* Real Safety Event History Audit Log */}
          <EventAuditLog isOnline={isOnline} />
        </div>
      </div>

      {/* Emergency SOS Modal (Only displays during critical SOS state) */}
      <EmergencyModal
        alarm={systemStatus?.alarm}
        location={systemStatus?.location}
        sessionData={systemStatus?.session}
        onReset={handleReset}
      />
    </div>
  );
}
