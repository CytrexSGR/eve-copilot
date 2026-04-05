import { Link } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

export function LandingHero() {
  const { login } = useAuth();

  return (
    <div style={{
      position: 'relative',
      background: 'linear-gradient(135deg, #0a0f1a 0%, #1a1f2e 50%, #0d1520 100%)',
      borderRadius: '12px',
      padding: '4rem 2rem',
      marginBottom: '2rem',
      border: '1px solid rgba(100, 150, 255, 0.15)',
      overflow: 'hidden',
      textAlign: 'center',
    }}>
      <div style={{
        position: 'absolute', top: 0, left: '50%', transform: 'translateX(-50%)',
        width: '600px', height: '300px',
        background: 'radial-gradient(ellipse at center top, rgba(0,212,255,0.08) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />
      <div style={{
        position: 'absolute', bottom: 0, right: 0,
        width: '400px', height: '400px',
        background: 'radial-gradient(circle at bottom right, rgba(168,85,247,0.06) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />

      <div style={{ position: 'relative', maxWidth: '700px', margin: '0 auto' }}>
        <div style={{
          display: 'inline-block',
          padding: '4px 12px',
          background: 'rgba(0, 212, 255, 0.1)',
          border: '1px solid rgba(0, 212, 255, 0.25)',
          borderRadius: '20px',
          fontSize: '0.7rem',
          fontWeight: 600,
          color: '#00d4ff',
          marginBottom: '1.25rem',
          letterSpacing: '0.05em',
        }}>
          EVE ONLINE INTELLIGENCE PLATFORM
        </div>

        <h1 style={{
          fontSize: '2.5rem',
          fontWeight: 800,
          lineHeight: 1.15,
          marginBottom: '1rem',
          background: 'linear-gradient(135deg, #fff 0%, #a0c4ff 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
        }}>
          Total Dominance<br />Starts With Intel
        </h1>

        <p style={{
          fontSize: '1.05rem',
          color: 'var(--text-secondary)',
          lineHeight: 1.6,
          marginBottom: '2rem',
          maxWidth: '550px',
          margin: '0 auto 2rem',
        }}>
          Real-time warfare intelligence, market analytics, fleet tools, and corporation management — everything you need to dominate New Eden.
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
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            Login with EVE SSO
          </button>
          <Link
            to="/pricing"
            style={{
              padding: '12px 28px',
              background: 'rgba(255, 204, 0, 0.1)',
              border: '1px solid rgba(255, 204, 0, 0.3)',
              borderRadius: '6px',
              color: '#ffcc00',
              fontSize: '0.9rem',
              fontWeight: 700,
              textDecoration: 'none',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            View Pricing
          </Link>
        </div>

        <div style={{
          marginTop: '2.5rem',
          display: 'flex',
          gap: '2rem',
          justifyContent: 'center',
          flexWrap: 'wrap',
        }}>
          {[
            { label: 'Intel Modules', value: '10+' },
            { label: 'Data Points / Hour', value: '100K+' },
            { label: 'Systems Tracked', value: '8,000+' },
            { label: 'Free Tier', value: 'Forever' },
          ].map(stat => (
            <div key={stat.label} style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#00d4ff' }}>{stat.value}</div>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{stat.label}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
