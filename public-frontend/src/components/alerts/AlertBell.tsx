import { useState, useRef, useEffect } from 'react';
import { useAlerts } from '../../hooks/useAlerts';
import { AlertPanel } from './AlertPanel';

export function AlertBell() {
  const { alerts, unreadCount, dismiss, dismissAll } = useAlerts();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          background: open ? 'rgba(255,255,255,0.06)' : 'transparent',
          border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: '4px', padding: '3px 7px',
          cursor: 'pointer', position: 'relative',
          color: unreadCount > 0 ? '#ff8800' : 'rgba(255,255,255,0.4)',
          fontSize: '0.85rem',
        }}
      >
        &#128276;
        {unreadCount > 0 && (
          <span style={{
            position: 'absolute', top: '-4px', right: '-4px',
            background: '#f85149', color: '#fff', borderRadius: '50%',
            width: 16, height: 16, fontSize: '0.55rem', fontWeight: 800,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>
      {open && (
        <AlertPanel
          alerts={alerts}
          onDismiss={dismiss}
          onDismissAll={dismissAll}
          onClose={() => setOpen(false)}
        />
      )}
    </div>
  );
}
