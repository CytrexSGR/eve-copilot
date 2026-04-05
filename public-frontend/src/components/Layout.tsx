import { useState, useRef, useEffect, useCallback, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { TIER_COLORS, TIER_LABELS } from '../types/auth';
import { AlertBell } from './alerts';
import { FeedbackWidget } from './FeedbackWidget';
import { EsiStatusBadge } from './common/EsiStatusBadge';

interface LayoutProps {
  children: ReactNode;
}

interface DropdownItem {
  to: string;
  label: string;
  color: string;
  logo?: string;
  logoSize?: number;
}

function NavDropdown({ label, color, items, isOpen, onOpen, onClose }: {
  label: string;
  color: string;
  items: DropdownItem[];
  isOpen: boolean;
  onOpen: () => void;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleEnter = useCallback(() => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    onOpen();
  }, [onOpen]);

  const handleLeave = useCallback(() => {
    timeoutRef.current = setTimeout(onClose, 150);
  }, [onClose]);

  useEffect(() => () => { if (timeoutRef.current) clearTimeout(timeoutRef.current); }, []);

  return (
    <div
      ref={ref}
      onMouseEnter={handleEnter}
      onMouseLeave={handleLeave}
      style={{ position: 'relative' }}
    >
      <button
        style={{
          background: isOpen ? 'rgba(255,255,255,0.06)' : 'transparent',
          border: `1px solid ${isOpen ? `${color}55` : 'transparent'}`,
          borderRadius: '4px',
          color,
          padding: '4px 10px',
          fontSize: '0.85rem',
          fontWeight: 600,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '0.3rem',
          whiteSpace: 'nowrap',
        }}
      >
        {label}
        <span style={{ fontSize: '0.6rem', opacity: 0.6, marginLeft: '2px' }}>&#9660;</span>
      </button>

      {isOpen && (
        <div style={{
          position: 'absolute',
          top: '100%',
          left: 0,
          marginTop: '4px',
          background: '#111827',
          border: '1px solid var(--border-color)',
          borderRadius: '6px',
          padding: '0.4rem 0',
          minWidth: '180px',
          zIndex: 1000,
          boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
        }}>
          {items.map(item => (
            <Link
              key={item.to}
              to={item.to}
              onClick={onClose}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.45rem 0.85rem',
                textDecoration: 'none',
                color: item.color,
                fontSize: '0.82rem',
                fontWeight: 500,
                whiteSpace: 'nowrap',
              }}
              onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.05)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
            >
              {item.logo && (
                <img src={item.logo} alt="" style={{
                  width: item.logoSize || 20, height: item.logoSize || 20, objectFit: 'contain',
                }} />
              )}
              {item.label}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

const INTEL_ITEMS: DropdownItem[] = [
  { to: '/battle-report', label: 'Warfare Intel', color: '#e6edf3', logo: '/warfare-intel-logo.png', logoSize: 22 },
  { to: '/war-economy', label: 'War Economy', color: '#e6edf3', logo: '/war-economy-logo.png', logoSize: 20 },
  { to: '/wormhole', label: 'Wormhole Intel', color: '#e6edf3', logo: '/wormhole-intel-logo.png', logoSize: 20 },
  { to: '/doctrines', label: 'Doctrine Intel', color: '#e6edf3', logo: '/doctrine-intel-logo.png', logoSize: 20 },
];

const TOOLS_ITEMS: DropdownItem[] = [
  { to: '/dashboard', label: 'Command Center', color: '#00d4ff' },
  { to: '/navigation', label: 'Navigation', color: '#00d4ff' },
  { to: '/shopping', label: 'Shopping', color: '#3fb950' },
  { to: '/intel', label: 'Intel Tools', color: '#f85149' },
  { to: '/characters', label: 'Characters', color: '#58a6ff' },
];

const PRODUCTION_ITEMS: DropdownItem[] = [
  { to: '/production', label: 'Production Suite', color: '#d29922' },
  { to: '/production/projects', label: 'Projects', color: '#d29922' },
  { to: '/production/pi', label: 'Planetary Industry', color: '#3fb950' },
];

const CORP_ITEMS: DropdownItem[] = [
  { to: '/corp', label: 'Dashboard', color: '#ffcc00' },
  { to: '/corp/finance', label: 'Finance', color: '#ffcc00' },
  { to: '/corp/hr', label: 'HR & Recruitment', color: '#00d4ff' },
  { to: '/corp/members', label: 'Members', color: '#00d4ff' },
  { to: '/corp/diplo', label: 'Diplomacy', color: '#3fb950' },
  { to: '/corp/srp', label: 'SRP', color: '#f85149' },
  { to: '/corp/fleet', label: 'Fleet Ops', color: '#f85149' },
  { to: '/corp/timers', label: 'Timers', color: '#ff8800' },
  { to: '/corp/tools', label: 'Corp Tools', color: '#a855f7' },
];

export function Layout({ children }: LayoutProps) {
  const { isLoggedIn, isLoading, account, activeCharacterId, setActiveCharacter, tierInfo, login, logout } = useAuth();
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);
  const [charSwitcherOpen, setCharSwitcherOpen] = useState(false);

  const linkStyle = (color: string) => ({
    textDecoration: 'none' as const,
    color,
    fontSize: '0.85rem',
    fontWeight: 600,
    padding: '4px 10px',
    border: `1px solid ${color}33`,
    borderRadius: '4px',
    whiteSpace: 'nowrap' as const,
  });

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <header style={{
        background: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border-color)',
        padding: '0.75rem 0'
      }}>
        <div className="container">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            {/* Logo area */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexShrink: 0 }}>
              <a href="https://evewho.com/corporation/98823773" target="_blank" rel="noopener noreferrer">
                <img
                  src="https://images.evetech.net/corporations/98823773/logo?size=64"
                  alt="Infinimind Intelligence"
                  style={{
                    width: '40px', height: '40px', borderRadius: '6px',
                    border: '2px solid var(--border-color)'
                  }}
                />
              </a>
              <div>
                <Link to="/" style={{ textDecoration: 'none' }}>
                  <h1 style={{ fontSize: '1.25rem', color: 'var(--accent-blue)', margin: 0 }}>
                    Infinimind Intelligence
                  </h1>
                </Link>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', margin: 0 }}>
                  EVE Real-time Intelligence
                </p>
              </div>
            </div>

            {/* Navigation */}
            <nav style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <NavDropdown
                label="Intelligence"
                color="#00d4ff"
                items={INTEL_ITEMS}
                isOpen={openDropdown === 'intel'}
                onOpen={() => setOpenDropdown('intel')}
                onClose={() => setOpenDropdown(null)}
              />

              <Link to="/market" style={linkStyle('#3fb950')}>Market</Link>

              <NavDropdown
                label="Production"
                color="#d29922"
                items={PRODUCTION_ITEMS}
                isOpen={openDropdown === 'production'}
                onOpen={() => setOpenDropdown('production')}
                onClose={() => setOpenDropdown(null)}
              />

              <Link to="/fittings" style={linkStyle('#a855f7')}>Fittings</Link>

              {isLoggedIn && (
                <>
                  <span style={{ color: 'rgba(255,255,255,0.15)', fontSize: '1.2rem', margin: '0 0.1rem' }}>|</span>

                  <NavDropdown
                    label="Pilot"
                    color="#58a6ff"
                    items={TOOLS_ITEMS}
                    isOpen={openDropdown === 'tools'}
                    onOpen={() => setOpenDropdown('tools')}
                    onClose={() => setOpenDropdown(null)}
                  />
                </>
              )}

              <span style={{ color: 'rgba(255,255,255,0.15)', fontSize: '1.2rem', margin: '0 0.1rem' }}>|</span>

              <NavDropdown
                label="Corporation"
                color="#ffcc00"
                items={CORP_ITEMS}
                isOpen={openDropdown === 'corp'}
                onOpen={() => setOpenDropdown('corp')}
                onClose={() => setOpenDropdown(null)}
              />

              {!isLoading && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginLeft: '0.25rem' }}>
                  {isLoggedIn && <AlertBell />}
                  {isLoggedIn && account && account.characters && account.characters.length > 1 && (
                    <div style={{ position: 'relative' }}>
                      <button
                        onClick={() => setCharSwitcherOpen(prev => !prev)}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.5rem',
                          background: 'transparent',
                          border: '1px solid var(--border-color)',
                          borderRadius: '4px',
                          padding: '4px 10px',
                          color: '#e6edf3',
                          cursor: 'pointer',
                          fontSize: '0.85rem',
                        }}
                      >
                        <img
                          src={`https://images.evetech.net/characters/${activeCharacterId || account.primary_character_id}/portrait?size=32`}
                          alt=""
                          style={{ width: 24, height: 24, borderRadius: '50%' }}
                        />
                        {account.characters.find(c => c.character_id === (activeCharacterId || account.primary_character_id))?.character_name || account.primary_character_name}
                        <span style={{ fontSize: '0.6rem', opacity: 0.6 }}>&#9660;</span>
                      </button>
                      {charSwitcherOpen && (
                        <div style={{
                          position: 'absolute',
                          top: '100%',
                          right: 0,
                          marginTop: '4px',
                          background: '#111827',
                          border: '1px solid var(--border-color)',
                          borderRadius: '6px',
                          padding: '0.4rem 0',
                          minWidth: '200px',
                          zIndex: 1000,
                          boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
                        }}>
                          {account.characters.map(char => (
                            <button
                              key={char.character_id}
                              onClick={() => {
                                setActiveCharacter(char.character_id);
                                setCharSwitcherOpen(false);
                              }}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.5rem',
                                width: '100%',
                                padding: '0.5rem 0.75rem',
                                background: char.character_id === (activeCharacterId || account.primary_character_id) ? 'rgba(0, 212, 255, 0.1)' : 'transparent',
                                border: 'none',
                                color: '#e6edf3',
                                cursor: 'pointer',
                                fontSize: '0.85rem',
                                textAlign: 'left' as const,
                              }}
                              onMouseEnter={e => {
                                if (char.character_id !== (activeCharacterId || account.primary_character_id)) {
                                  e.currentTarget.style.background = 'rgba(255,255,255,0.05)';
                                }
                              }}
                              onMouseLeave={e => {
                                e.currentTarget.style.background = char.character_id === (activeCharacterId || account.primary_character_id) ? 'rgba(0, 212, 255, 0.1)' : 'transparent';
                              }}
                            >
                              <img
                                src={`https://images.evetech.net/characters/${char.character_id}/portrait?size=32`}
                                alt=""
                                style={{ width: 24, height: 24, borderRadius: '50%' }}
                              />
                              {char.character_name}
                              {char.is_primary && (
                                <span style={{ fontSize: '0.65rem', color: '#d4a017', marginLeft: 'auto' }}>PRIMARY</span>
                              )}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                  {isLoggedIn && account ? (
                    <>
                      <span style={{
                        padding: '3px 7px',
                        background: `${TIER_COLORS[tierInfo?.tier || 'free']}22`,
                        border: `1px solid ${TIER_COLORS[tierInfo?.tier || 'free']}55`,
                        color: TIER_COLORS[tierInfo?.tier || 'free'],
                        borderRadius: '3px',
                        fontSize: '0.65rem',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                      }}>
                        {TIER_LABELS[tierInfo?.tier || 'free']}
                      </span>
                      <Link to="/account" style={{
                        display: 'flex', alignItems: 'center', gap: '0.35rem',
                        textDecoration: 'none', color: 'inherit',
                      }}>
                        <img
                          src={`https://images.evetech.net/characters/${account.primary_character_id}/portrait?size=32`}
                          alt={account.primary_character_name}
                          style={{ width: 26, height: 26, borderRadius: '50%', border: '1px solid var(--border-color)' }}
                        />
                      </Link>
                      <button
                        onClick={logout}
                        style={{
                          background: 'none',
                          border: '1px solid rgba(255,255,255,0.12)',
                          color: 'var(--text-secondary)',
                          padding: '3px 8px',
                          borderRadius: '4px',
                          fontSize: '0.7rem',
                          cursor: 'pointer',
                        }}
                      >
                        Logout
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={login}
                      style={{
                        background: 'linear-gradient(135deg, #1a3a5c, #0d2137)',
                        border: '1px solid rgba(0, 212, 255, 0.3)',
                        color: '#00d4ff',
                        padding: '5px 12px',
                        borderRadius: '4px',
                        fontSize: '0.8rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.4rem',
                      }}
                    >
                      Login with EVE
                    </button>
                  )}
                </div>
              )}
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main style={{ flex: 1, padding: '2rem 0' }}>
        <div className="container">
          {children}
        </div>
      </main>

      {/* Footer */}
      <footer style={{
        background: 'var(--bg-secondary)',
        borderTop: '1px solid var(--border-color)',
        padding: '2rem 0',
        marginTop: '3rem'
      }}>
        <div className="container">
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '2rem'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', margin: 0 }}>
                &copy; 2026 Infinimind Creations | Data from zKillboard &amp; ESI
              </p>
              <EsiStatusBadge />
            </div>
            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
              <span style={{ color: 'rgba(255,255,255,0.3)', fontSize: '0.8rem', fontWeight: 600 }}>Intel</span>
              <Link to="/battle-report" style={{ fontSize: '0.8rem' }}>Warfare</Link>
              <Link to="/war-economy" style={{ fontSize: '0.8rem' }}>Economy</Link>
              <Link to="/wormhole" style={{ fontSize: '0.8rem' }}>Wormholes</Link>
              <Link to="/doctrines" style={{ fontSize: '0.8rem' }}>Doctrines</Link>
              <span style={{ color: 'rgba(255,255,255,0.15)' }}>|</span>
              <span style={{ color: 'rgba(255,255,255,0.3)', fontSize: '0.8rem', fontWeight: 600 }}>Tools</span>
              <Link to="/market" style={{ fontSize: '0.8rem' }}>Market</Link>
              <Link to="/production" style={{ fontSize: '0.8rem' }}>Production</Link>
              <Link to="/production/pi" style={{ fontSize: '0.8rem' }}>PI</Link>
              <Link to="/fittings" style={{ fontSize: '0.8rem' }}>Fittings</Link>
              <Link to="/navigation" style={{ fontSize: '0.8rem' }}>Navigation</Link>
              <Link to="/shopping" style={{ fontSize: '0.8rem' }}>Shopping</Link>
              <span style={{ color: 'rgba(255,255,255,0.15)' }}>|</span>
              <span style={{ color: 'rgba(255,255,255,0.3)', fontSize: '0.8rem', fontWeight: 600 }}>Corp</span>
              <Link to="/corp/finance" style={{ fontSize: '0.8rem' }}>Finance</Link>
              <Link to="/corp/hr" style={{ fontSize: '0.8rem' }}>HR</Link>
              <Link to="/corp/srp" style={{ fontSize: '0.8rem' }}>SRP</Link>
              <Link to="/corp/fleet" style={{ fontSize: '0.8rem' }}>Fleet</Link>
              <Link to="/corp/timers" style={{ fontSize: '0.8rem' }}>Timers</Link>
              <span style={{ color: 'rgba(255,255,255,0.15)' }}>|</span>
              <span style={{ color: 'rgba(255,255,255,0.3)', fontSize: '0.8rem', fontWeight: 600 }}>Community</span>
              <a href="https://discord.gg/evecopilot" target="_blank" rel="noopener noreferrer" style={{ fontSize: '0.8rem' }}>Discord</a>
              <a href="https://github.com/CytrexSGR/Eve-Online-Copilot" target="_blank" rel="noopener noreferrer" style={{ fontSize: '0.8rem' }}>GitHub</a>
              <span style={{ color: 'rgba(255,255,255,0.15)' }}>|</span>
              <Link to="/pricing" style={{ fontSize: '0.8rem' }}>Pricing</Link>
              <Link to="/how-it-works" style={{ fontSize: '0.8rem' }}>How It Works</Link>
              <Link to="/impressum" style={{ fontSize: '0.8rem' }}>Legal</Link>
              <Link to="/datenschutz" style={{ fontSize: '0.8rem' }}>Privacy</Link>
            </div>
          </div>
          <p style={{ color: 'var(--text-tertiary)', fontSize: '0.75rem', marginTop: '0.75rem' }}>
            EVE Online and the EVE logo are trademarks of CCP hf.
          </p>
        </div>
      </footer>
      <FeedbackWidget />
    </div>
  );
}
