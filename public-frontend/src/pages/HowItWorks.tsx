import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

const STEPS = [
  {
    number: '01',
    title: 'Login with EVE SSO',
    description: 'Sign in securely through CCP\'s official Single Sign-On. We never see your password — only your public character info.',
    color: '#00d4ff',
  },
  {
    number: '02',
    title: 'Explore Free Features',
    description: 'The free tier includes the live map, basic market data, ship database, entity overviews, and intel previews. No ISK required.',
    color: '#3fb950',
  },
  {
    number: '03',
    title: 'Unlock Intel Modules',
    description: 'Each intel module (Warfare, Economy, Wormhole, Doctrine, Battle) is 100M ISK/month with a free 24-hour trial.',
    color: '#d29922',
  },
  {
    number: '04',
    title: 'Scale to Your Corp',
    description: 'Corporation and alliance plans unlock fleet tools, SRP, finance dashboards, HR management, and more for your entire organization.',
    color: '#ffcc00',
  },
];

const FEATURES = [
  {
    title: 'Real-Time LiveMap',
    description: 'Interactive sovereignty map with live battle markers, sov campaign overlays, and activity heat visualization. Always free.',
    tier: 'Free',
    tierColor: '#8b949e',
  },
  {
    title: 'Coalition Warfare Intel',
    description: 'Track every coalition in nullsec — kill efficiency, fleet compositions, capital movements, and strategic trends over 7-30 day windows.',
    tier: 'Module',
    tierColor: '#f85149',
  },
  {
    title: 'Market Analysis',
    description: '5-hub price comparison, historical trends, volatility scoring, and automated arbitrage route discovery with fee-accurate profit calculation.',
    tier: 'Module',
    tierColor: '#58a6ff',
  },
  {
    title: 'Fleet Operations',
    description: 'PAP tracking, D-Scan parser, local scan analysis, structure timers, and SRP claim management for fleet commanders.',
    tier: 'Corp',
    tierColor: '#ffcc00',
  },
  {
    title: 'Finance Dashboard',
    description: 'Corporation wallet monitoring, mining tax tracking, invoice generation, and buyback program management with Janice API integration.',
    tier: 'Corp',
    tierColor: '#ffcc00',
  },
  {
    title: 'Multi-Character Dashboard',
    description: 'Unified view across all your characters — skill queues, assets, industry jobs, and wallet balances in one place.',
    tier: 'Module',
    tierColor: '#00d4ff',
  },
];

const FAQ = [
  {
    q: 'Is it safe to login with EVE SSO?',
    a: 'Yes. We use CCP\'s official OAuth2 flow. We never see your password. All tokens are encrypted at rest with Fernet encryption and auto-refreshed.',
  },
  {
    q: 'How do I pay?',
    a: 'All payments are in-game ISK. Select a module or plan, receive a unique payment code, and send ISK to our holding character with the code as reason. Your subscription activates within minutes.',
  },
  {
    q: 'What\'s included in the free tier?',
    a: 'The live map, basic Jita market data, ship database, entity overviews, and 1-hour intel previews. You can use these features forever without paying.',
  },
  {
    q: 'Can I try before I buy?',
    a: 'Every module includes a free 24-hour trial. No ISK needed — just click "Try 24H Free" on the Pricing page.',
  },
  {
    q: 'How does corporation pricing work?',
    a: 'Corp plans are seat-based. You pick how many "heavy seats" you need (users who get entity deep-dives and battle analysis). All members automatically get intel modules and basic features.',
  },
  {
    q: 'Is this allowed by CCP?',
    a: 'We only use CCP\'s official ESI API and follow their third-party developer license. ISK-based payments are a common model for EVE services.',
  },
];

export function HowItWorks() {
  const { isLoggedIn, login } = useAuth();

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '0 1rem' }}>
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
        <h1 style={{ fontSize: '2rem', fontWeight: 700, marginBottom: '0.4rem' }}>
          How It Works
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '1rem' }}>
          From login to total intel dominance in 4 steps.
        </p>
      </div>

      {/* Steps */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '3rem' }}>
        {STEPS.map(step => (
          <div key={step.number} style={{
            background: 'var(--bg-secondary)',
            border: `1px solid ${step.color}22`,
            borderRadius: '8px',
            padding: '1.25rem',
            position: 'relative',
          }}>
            <div style={{
              fontSize: '2rem',
              fontWeight: 800,
              color: `${step.color}20`,
              position: 'absolute',
              top: '0.75rem',
              right: '1rem',
              lineHeight: 1,
            }}>
              {step.number}
            </div>
            <div style={{ fontSize: '0.9rem', fontWeight: 700, color: step.color, marginBottom: '0.5rem' }}>
              {step.title}
            </div>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: 1.5, margin: 0 }}>
              {step.description}
            </p>
          </div>
        ))}
      </div>

      {/* Feature walkthrough */}
      <div style={{ marginBottom: '3rem' }}>
        <h2 style={{ fontSize: '1.3rem', fontWeight: 700, marginBottom: '1rem', textAlign: 'center' }}>
          Platform Capabilities
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.75rem' }}>
          {FEATURES.map(feat => (
            <div key={feat.title} style={{
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              padding: '1rem 1.25rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.3rem',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary)' }}>{feat.title}</span>
                <span style={{
                  padding: '2px 8px',
                  borderRadius: '10px',
                  fontSize: '0.6rem',
                  fontWeight: 700,
                  background: `${feat.tierColor}18`,
                  color: feat.tierColor,
                  border: `1px solid ${feat.tierColor}33`,
                }}>
                  {feat.tier}
                </span>
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: 1.5, margin: 0 }}>
                {feat.description}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* FAQ */}
      <div style={{ marginBottom: '2.5rem' }}>
        <h2 style={{ fontSize: '1.3rem', fontWeight: 700, marginBottom: '1rem', textAlign: 'center' }}>
          Frequently Asked Questions
        </h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {FAQ.map(item => (
            <div key={item.q} style={{
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              padding: '1rem 1.25rem',
            }}>
              <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.35rem' }}>
                {item.q}
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: 1.5, margin: 0 }}>
                {item.a}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Bottom CTA */}
      <div style={{
        background: 'linear-gradient(135deg, #0d1520 0%, #1a1f2e 100%)',
        border: '1px solid rgba(100, 150, 255, 0.15)',
        borderRadius: '12px',
        padding: '2.5rem 2rem',
        textAlign: 'center',
        marginBottom: '1rem',
      }}>
        <h3 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '0.75rem' }}>
          Start Your Intel Advantage Today
        </h3>
        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
          {!isLoggedIn ? (
            <button onClick={login} style={{
              padding: '10px 24px', background: 'linear-gradient(135deg, #00d4ff, #0088cc)',
              border: 'none', borderRadius: '6px', color: '#000', fontSize: '0.85rem', fontWeight: 700, cursor: 'pointer',
            }}>
              Login with EVE SSO
            </button>
          ) : (
            <Link to="/dashboard" style={{
              padding: '10px 24px', background: 'linear-gradient(135deg, #00d4ff, #0088cc)',
              border: 'none', borderRadius: '6px', color: '#000', fontSize: '0.85rem', fontWeight: 700, textDecoration: 'none',
            }}>
              Go to Dashboard
            </Link>
          )}
          <Link to="/pricing" style={{
            padding: '10px 24px', background: 'rgba(255,204,0,0.1)', border: '1px solid rgba(255,204,0,0.3)',
            borderRadius: '6px', color: '#ffcc00', fontSize: '0.85rem', fontWeight: 700, textDecoration: 'none',
          }}>
            View Pricing
          </Link>
        </div>
      </div>
    </div>
  );
}
