import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export function AuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const success = searchParams.get('success');
    const errorMsg = searchParams.get('error');
    const token = searchParams.get('token');

    if (errorMsg) {
      setError(errorMsg);
      return;
    }

    if (success === 'true' && token) {
      // Set session cookie on the current origin (avoids cross-origin cookie issues)
      document.cookie = `session=${token}; path=/; max-age=${30 * 24 * 60 * 60}; SameSite=Lax`;
      localStorage.setItem('eve_auth', '1');
      refresh().then(() => navigate('/', { replace: true }));
    } else if (success === 'true') {
      // Legacy flow without token param
      localStorage.setItem('eve_auth', '1');
      refresh().then(() => navigate('/', { replace: true }));
    } else {
      setError('Authentication failed');
    }
  }, [searchParams, navigate, refresh]);

  if (error) {
    return (
      <div style={{ textAlign: 'center', padding: '4rem 1rem' }}>
        <h2 style={{ color: '#ff4444', marginBottom: '1rem' }}>Login Failed</h2>
        <p style={{ color: 'var(--text-secondary)' }}>{error}</p>
        <button
          onClick={() => navigate('/')}
          style={{
            marginTop: '1.5rem',
            background: 'var(--bg-tertiary)',
            border: '1px solid var(--border-color)',
            color: 'inherit',
            padding: '8px 20px',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          Back to Home
        </button>
      </div>
    );
  }

  return (
    <div style={{ textAlign: 'center', padding: '4rem 1rem' }}>
      <p style={{ color: 'var(--text-secondary)' }}>Authenticating...</p>
    </div>
  );
}
