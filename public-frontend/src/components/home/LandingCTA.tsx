import { Link } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

export function LandingCTA() {
  const { login } = useAuth();

  return (
    <div style={{
      background: 'linear-gradient(135deg, #0d1520 0%, #1a1f2e 100%)',
      border: '1px solid rgba(100, 150, 255, 0.15)',
      borderRadius: '12px',
      padding: '3rem 2rem',
      textAlign: 'center',
      marginBottom: '1rem',
    }}>
      <h2 style={{
        fontSize: '1.6rem',
        fontWeight: 700,
        marginBottom: '0.5rem',
        background: 'linear-gradient(135deg, #fff 0%, #a0c4ff 100%)',
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
      }}>
        Ready to Dominate?
      </h2>
      <p style={{
        color: 'var(--text-secondary)',
        fontSize: '0.9rem',
        marginBottom: '1.5rem',
        maxWidth: '500px',
        margin: '0 auto 1.5rem',
      }}>
        Start with our free tier — no credit card, no ISK required. Upgrade anytime with in-game ISK.
      </p>
      <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center', flexWrap: 'wrap' }}>
        <button
          onClick={login}
          style={{
            padding: '12px 28px',
            background: 'linear-gradient(135deg, #00d4ff, #0088cc)',
            border: 'none',
            borderRadius: '6px',
            color: '#000',
            fontSize: '0.9rem',
            fontWeight: 700,
            cursor: 'pointer',
          }}
        >
          Get Started Free
        </button>
        <Link
          to="/how-it-works"
          style={{
            padding: '12px 28px',
            background: 'rgba(255,255,255,0.05)',
            border: '1px solid rgba(255,255,255,0.15)',
            borderRadius: '6px',
            color: 'var(--text-primary)',
            fontSize: '0.9rem',
            fontWeight: 600,
            textDecoration: 'none',
          }}
        >
          How It Works
        </Link>
      </div>
    </div>
  );
}
