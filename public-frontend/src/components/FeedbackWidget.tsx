import { useState, useRef, useEffect } from 'react';

const CATEGORIES = [
  { value: 'bug', label: 'Bug Report', color: '#f85149' },
  { value: 'feature', label: 'Feature Request', color: '#3fb950' },
  { value: 'ux', label: 'UX / Design', color: '#d29922' },
  { value: 'other', label: 'Other', color: '#8b949e' },
];

export function FeedbackWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [category, setCategory] = useState('bug');
  const [message, setMessage] = useState('');
  const [status, setStatus] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle');
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: MouseEvent) => {
      if (modalRef.current && !modalRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [isOpen]);

  const handleSubmit = async () => {
    if (message.trim().length < 10) return;
    setStatus('sending');
    try {
      const res = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          category,
          message: message.trim(),
          page_url: window.location.pathname,
        }),
      });
      if (!res.ok) throw new Error('Failed');
      setStatus('sent');
      setTimeout(() => {
        setIsOpen(false);
        setStatus('idle');
        setMessage('');
        setCategory('bug');
      }, 1500);
    } catch {
      setStatus('error');
    }
  };

  const selectedCat = CATEGORIES.find(c => c.value === category);

  return (
    <>
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          position: 'fixed',
          bottom: '1.5rem',
          right: '1.5rem',
          zIndex: 9999,
          background: 'linear-gradient(135deg, #1a3a5c, #0d2137)',
          border: '1px solid rgba(0, 212, 255, 0.3)',
          color: '#00d4ff',
          width: '48px',
          height: '48px',
          borderRadius: '50%',
          fontSize: '1.2rem',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.4)',
          transition: 'transform 0.2s, box-shadow 0.2s',
        }}
        onMouseEnter={e => {
          e.currentTarget.style.transform = 'scale(1.1)';
          e.currentTarget.style.boxShadow = '0 6px 24px rgba(0, 212, 255, 0.3)';
        }}
        onMouseLeave={e => {
          e.currentTarget.style.transform = 'scale(1)';
          e.currentTarget.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.4)';
        }}
        title="Send Feedback"
      >
        {isOpen ? '\u2715' : '\u2709'}
      </button>

      {isOpen && (
        <div style={{
          position: 'fixed',
          inset: 0,
          zIndex: 9998,
          display: 'flex',
          alignItems: 'flex-end',
          justifyContent: 'flex-end',
          padding: '0 1.5rem 5.5rem 0',
        }}>
          <div
            ref={modalRef}
            style={{
              background: '#111827',
              border: '1px solid var(--border-color)',
              borderRadius: '10px',
              padding: '1.25rem',
              width: '340px',
              boxShadow: '0 12px 40px rgba(0, 0, 0, 0.6)',
            }}
          >
            <div style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '0.75rem', color: 'var(--text-primary)' }}>
              Send Feedback
            </div>

            <div style={{ display: 'flex', gap: '0.4rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
              {CATEGORIES.map(cat => (
                <button
                  key={cat.value}
                  onClick={() => setCategory(cat.value)}
                  style={{
                    padding: '4px 10px',
                    borderRadius: '12px',
                    fontSize: '0.7rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    border: `1px solid ${cat.value === category ? cat.color : 'var(--border-color)'}`,
                    background: cat.value === category ? `${cat.color}22` : 'transparent',
                    color: cat.value === category ? cat.color : 'var(--text-secondary)',
                  }}
                >
                  {cat.label}
                </button>
              ))}
            </div>

            <textarea
              value={message}
              onChange={e => setMessage(e.target.value)}
              placeholder="Describe your feedback... (min 10 characters)"
              rows={4}
              style={{
                width: '100%',
                background: 'var(--bg-primary)',
                border: '1px solid var(--border-color)',
                borderRadius: '6px',
                padding: '0.6rem',
                color: 'var(--text-primary)',
                fontSize: '0.8rem',
                resize: 'vertical',
                fontFamily: 'inherit',
                boxSizing: 'border-box',
              }}
            />

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.6rem' }}>
              <span style={{ fontSize: '0.65rem', color: 'var(--text-tertiary)' }}>
                {message.length}/2000
              </span>
              <button
                onClick={handleSubmit}
                disabled={status === 'sending' || status === 'sent' || message.trim().length < 10}
                style={{
                  padding: '6px 16px',
                  borderRadius: '4px',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  cursor: status === 'sending' || message.trim().length < 10 ? 'default' : 'pointer',
                  border: 'none',
                  background: status === 'sent' ? '#3fb950' : status === 'error' ? '#f85149' : `${selectedCat?.color || '#00d4ff'}`,
                  color: '#000',
                  opacity: message.trim().length < 10 ? 0.4 : 1,
                }}
              >
                {status === 'sending' ? 'Sending...' : status === 'sent' ? 'Sent!' : status === 'error' ? 'Retry' : 'Send'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
