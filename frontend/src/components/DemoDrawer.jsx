import React, { useState } from 'react';
import { Sparkles, EyeOff, Smile, AlertOctagon, RotateCcw, ChevronDown, ChevronUp } from 'lucide-react';

export default function DemoDrawer({ onReset }) {
  const [isOpen, setIsOpen] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const triggerAction = async (action) => {
    try {
      const res = await fetch('/api/test/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action })
      });
      const data = await res.json();
      setFeedback(data.message || 'Action sent');
      setTimeout(() => setFeedback(null), 3000);
    } catch (e) {
      setFeedback('Error sending simulation action');
      setTimeout(() => setFeedback(null), 3000);
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '0.85rem 1.25rem', display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
      <div
        onClick={() => setIsOpen(!isOpen)}
        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Sparkles size={16} color="#00F0FF" />
          <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-main)', textTransform: 'uppercase' }}>
            Academic Project Demonstration Toolkit
          </h4>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {feedback && (
            <span style={{ fontSize: '0.72rem', color: '#34D399', fontFamily: 'var(--font-mono)' }}>
              {feedback}
            </span>
          )}
          {isOpen ? <ChevronUp size={16} color="var(--text-muted)" /> : <ChevronDown size={16} color="var(--text-muted)" />}
        </div>
      </div>

      {isOpen && (
        <div style={{ paddingTop: '0.5rem', borderTop: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: 1.4 }}>
            Instantly trigger simulated physiological events to demonstrate system workflows to evaluation committees:
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '0.5rem' }}>
            <button
              onClick={() => triggerAction('drowsy')}
              style={{
                padding: '0.5rem',
                borderRadius: 'var(--radius-sm)',
                background: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid rgba(239, 68, 68, 0.35)',
                color: '#F87171',
                fontSize: '0.75rem',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.35rem'
              }}
            >
              <EyeOff size={14} />
              Simulate Drowsy
            </button>

            <button
              onClick={() => triggerAction('yawn')}
              style={{
                padding: '0.5rem',
                borderRadius: 'var(--radius-sm)',
                background: 'rgba(249, 115, 22, 0.15)',
                border: '1px solid rgba(249, 115, 22, 0.35)',
                color: '#FB923C',
                fontSize: '0.75rem',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.35rem'
              }}
            >
              <Smile size={14} />
              Simulate Yawn
            </button>

            <button
              onClick={() => triggerAction('emergency')}
              style={{
                padding: '0.5rem',
                borderRadius: 'var(--radius-sm)',
                background: 'rgba(239, 68, 68, 0.25)',
                border: '1px solid #EF4444',
                color: '#FCA5A5',
                fontSize: '0.75rem',
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.35rem'
              }}
            >
              <AlertOctagon size={14} />
              Simulate SOS
            </button>

            <button
              onClick={() => triggerAction('reset')}
              style={{
                padding: '0.5rem',
                borderRadius: 'var(--radius-sm)',
                background: 'rgba(16, 185, 129, 0.15)',
                border: '1px solid rgba(16, 185, 129, 0.35)',
                color: '#34D399',
                fontSize: '0.75rem',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.35rem'
              }}
            >
              <RotateCcw size={14} />
              Reset Normal
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
