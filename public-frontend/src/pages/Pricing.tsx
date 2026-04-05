import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useModules } from '../hooks/useModules';
import { moduleApi } from '../services/api/auth';

// --- Module definitions ---

interface Module {
  id: string;
  name: string;
  icon: string;
  description: string;
  price: string;
  features: string[];
  color: string;
}

interface EntityTier {
  scope: string;
  corp: string;
  alliance: string;
  powerbloc: string;
}

interface OrgPlan {
  name: string;
  seats: number;
  price: string;
  highlight?: boolean;
}

interface Bundle {
  name: string;
  description: string;
  price: string;
  savings: string;
  modules: string[];
  color: string;
  highlight?: boolean;
}

const INTEL_MODULES: Module[] = [
  {
    id: 'warfare_intel',
    name: 'Warfare Intel',
    icon: '\u2694\uFE0F',
    description: 'Battle Reports & Coalition Wars',
    price: '100M',
    features: ['3 tabs (Battlefield, Alliances, Intelligence)', 'All timeframes (10M\u20137D)', 'Capital Intel & Trade Routes'],
    color: '#f85149',
  },
  {
    id: 'war_economy',
    name: 'War Economy',
    icon: '\uD83D\uDCB0',
    description: 'Economic Warfare Intelligence',
    price: '100M',
    features: ['5 tabs (Combat, Trading, Routes, Signals, Intel)', 'All timeframes', 'Fuel trends & manipulation alerts'],
    color: '#d29922',
  },
  {
    id: 'wormhole_intel',
    name: 'Wormhole Intel',
    icon: '\uD83C\uDF00',
    description: 'J-Space Hunting & Recon',
    price: '100M',
    features: ['4 tabs (Hunters, Residents, Market, Thera)', 'Class filters (C1\u2013C6)', 'Thera Route Calculator'],
    color: '#a855f7',
  },
  {
    id: 'doctrine_intel',
    name: 'Doctrine Intel',
    icon: '\uD83D\uDCCB',
    description: 'Fleet Composition Tracking',
    price: '100M',
    features: ['3 tabs (Live Ops, Intel, Trends)', 'Counter recommendations', 'Usage trends & ship distribution'],
    color: '#3fb950',
  },
  {
    id: 'battle_analysis',
    name: 'Battle Analysis',
    icon: '\uD83D\uDCA5',
    description: 'Deep Battle Breakdown',
    price: '100M',
    features: ['13 analysis panels', 'Dogma Engine tank profiles', 'Attacker loadouts & timeline'],
    color: '#ff6a00',
  },
];

const PERSONAL_MODULES: Module[] = [
  {
    id: 'character_suite',
    name: 'Character Suite',
    icon: '\uD83D\uDC64',
    description: 'Personal Pilot Dashboard',
    price: '150M',
    features: ['Skills & training queue', 'Valued assets by location', 'Industry jobs & blueprints'],
    color: '#00d4ff',
  },
  {
    id: 'market_analysis',
    name: 'Market Analysis',
    icon: '\uD83D\uDCC8',
    description: 'Advanced Trade Intelligence',
    price: '150M',
    features: ['5-hub price comparison', 'Price trends & volatility', 'Arbitrage opportunities'],
    color: '#58a6ff',
  },
];

const ENTITY_TIERS: EntityTier[] = [
  { scope: '1 Entity', corp: '50M', alliance: '75M', powerbloc: '100M' },
  { scope: '5 Entities', corp: '150M', alliance: '200M', powerbloc: '250M' },
  { scope: 'Unlimited', corp: '200M', alliance: '250M', powerbloc: '300M' },
];

const BUNDLES: Bundle[] = [
  {
    name: 'Intel Pack',
    description: '5 Intel modules',
    price: '350M',
    savings: '30%',
    modules: ['Warfare', 'War Economy', 'Wormhole', 'Doctrine', 'Battle'],
    color: '#f85149',
  },
  {
    name: 'Entity Pack',
    description: '3 Entity modules (Unlimited)',
    price: '550M',
    savings: '27%',
    modules: ['Corp Intel', 'Alliance Intel', 'PowerBloc Intel'],
    color: '#ffcc00',
  },
  {
    name: 'Pilot Complete',
    description: 'All 10 modules',
    price: '1B',
    savings: '40%',
    modules: ['All Intel', 'All Entity', 'Character', 'Market'],
    color: '#00d4ff',
    highlight: true,
  },
];

const CORP_PLANS: OrgPlan[] = [
  { name: 'Starter', seats: 5, price: '500M' },
  { name: 'Standard', seats: 15, price: '1.5B', highlight: true },
  { name: 'Professional', seats: 30, price: '2.5B' },
];

const ALLIANCE_PLANS: OrgPlan[] = [
  { name: 'Standard', seats: 15, price: '2.5B' },
  { name: 'Professional', seats: 40, price: '4B', highlight: true },
  { name: 'Enterprise', seats: 75, price: '6B' },
];

// --- Styles ---

const sectionTitle: React.CSSProperties = {
  fontSize: '0.7rem',
  fontWeight: 700,
  letterSpacing: '0.15em',
  textTransform: 'uppercase' as const,
  color: 'var(--text-secondary)',
  marginBottom: '1rem',
  paddingBottom: '0.5rem',
  borderBottom: '1px solid var(--border-color)',
};

const cardBase: React.CSSProperties = {
  background: 'var(--bg-secondary)',
  border: '1px solid var(--border-color)',
  borderRadius: '8px',
  padding: '1.25rem',
  display: 'flex',
  flexDirection: 'column',
};

// --- Components ---

function ModuleCard({ mod, isOwned, isLoggedIn, onLogin, onTrialActivated }: {
  mod: Module;
  isOwned: boolean;
  isLoggedIn: boolean;
  onLogin: () => void;
  onTrialActivated: () => void;
}) {
  const [trialLoading, setTrialLoading] = useState(false);
  const [trialError, setTrialError] = useState<string | null>(null);
  const [trialSuccess, setTrialSuccess] = useState(false);

  const handleTrial = async () => {
    if (!isLoggedIn) { onLogin(); return; }
    setTrialLoading(true);
    setTrialError(null);
    try {
      await moduleApi.activateTrial(mod.id);
      setTrialSuccess(true);
      onTrialActivated();
    } catch (err: unknown) {
      const error = err as { response?: { status?: number } };
      if (error?.response?.status === 409) setTrialError('Trial already used');
      else if (error?.response?.status === 401) setTrialError('Login required');
      else setTrialError('Activation failed');
    } finally {
      setTrialLoading(false);
    }
  };

  return (
    <div style={{
      ...cardBase,
      borderColor: isOwned ? `${mod.color}66` : `${mod.color}33`,
      transition: 'border-color 0.2s',
      minHeight: 220,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
        <span style={{ fontSize: '1.1rem' }}>{mod.icon}</span>
        <span style={{ fontSize: '0.95rem', fontWeight: 700, color: mod.color }}>{mod.name}</span>
        {isOwned && (
          <span style={{
            marginLeft: 'auto',
            padding: '1px 6px',
            background: 'rgba(63,185,80,0.2)',
            border: '1px solid rgba(63,185,80,0.4)',
            borderRadius: '3px',
            fontSize: '0.6rem',
            fontWeight: 700,
            color: '#3fb950',
          }}>ACTIVE</span>
        )}
      </div>
      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
        {mod.description}
      </div>
      <div style={{ flex: 1 }}>
        {mod.features.map((f, i) => (
          <div key={i} style={{ display: 'flex', gap: '0.4rem', fontSize: '0.75rem', marginBottom: '0.3rem', color: 'var(--text-primary)' }}>
            <span style={{ color: mod.color, flexShrink: 0 }}>&#10003;</span>
            <span>{f}</span>
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: `1px solid ${mod.color}22` }}>
        <span style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)' }}>{mod.price}</span>
        <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>/ 30 days</span>
      </div>
      {isOwned ? (
        <div style={{
          marginTop: '0.5rem',
          background: 'rgba(63,185,80,0.1)',
          border: '1px solid rgba(63,185,80,0.3)',
          padding: '6px 0',
          borderRadius: '4px',
          fontSize: '0.75rem',
          fontWeight: 600,
          color: '#3fb950',
          textAlign: 'center',
        }}>
          &#10003; Subscribed
        </div>
      ) : trialSuccess ? (
        <div style={{
          marginTop: '0.5rem',
          background: 'rgba(63,185,80,0.1)',
          border: '1px solid rgba(63,185,80,0.3)',
          padding: '6px 0',
          borderRadius: '4px',
          fontSize: '0.75rem',
          fontWeight: 600,
          color: '#3fb950',
          textAlign: 'center',
        }}>
          Trial Active (24H)
        </div>
      ) : (
        <>
          {trialError && (
            <div style={{ fontSize: '0.7rem', color: '#f85149', marginTop: '0.3rem', textAlign: 'center' }}>{trialError}</div>
          )}
          <button
            onClick={handleTrial}
            disabled={trialLoading}
            style={{
              marginTop: '0.5rem',
              background: `${mod.color}15`,
              border: `1px solid ${mod.color}44`,
              color: mod.color,
              padding: '6px 0',
              borderRadius: '4px',
              fontSize: '0.75rem',
              fontWeight: 600,
              cursor: trialLoading ? 'wait' : 'pointer',
              width: '100%',
              opacity: trialLoading ? 0.6 : 1,
            }}
          >
            {trialLoading ? 'Activating...' : isLoggedIn ? 'Try 24H Free' : 'Sign In to Try'}
          </button>
        </>
      )}
    </div>
  );
}

function BundleCard({ bundle }: { bundle: Bundle }) {
  return (
    <div style={{
      ...cardBase,
      borderColor: bundle.highlight ? `${bundle.color}55` : `${bundle.color}33`,
      boxShadow: bundle.highlight ? `0 0 20px ${bundle.color}15` : undefined,
      position: 'relative',
    }}>
      {bundle.highlight && (
        <div style={{
          position: 'absolute',
          top: '-10px',
          left: '50%',
          transform: 'translateX(-50%)',
          background: bundle.color,
          color: '#000',
          padding: '2px 10px',
          borderRadius: '10px',
          fontSize: '0.6rem',
          fontWeight: 700,
          letterSpacing: '0.05em',
        }}>
          BEST VALUE
        </div>
      )}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
        <div>
          <div style={{ fontSize: '1rem', fontWeight: 700, color: bundle.color }}>{bundle.name}</div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{bundle.description}</div>
        </div>
        <div style={{
          background: `${bundle.color}22`,
          color: bundle.color,
          padding: '2px 8px',
          borderRadius: '10px',
          fontSize: '0.65rem',
          fontWeight: 700,
          whiteSpace: 'nowrap',
        }}>
          {bundle.savings} OFF
        </div>
      </div>
      <div style={{ flex: 1, marginBottom: '0.5rem' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
          {bundle.modules.map((m, i) => (
            <span key={i} style={{
              fontSize: '0.6rem',
              padding: '1px 6px',
              borderRadius: '3px',
              background: 'var(--bg-hover)',
              color: 'var(--text-primary)',
            }}>{m}</span>
          ))}
        </div>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <span style={{ fontSize: '1.3rem', fontWeight: 700, color: 'var(--text-primary)' }}>{bundle.price}</span>
          <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', marginLeft: '0.3rem' }}>/ 30d</span>
        </div>
        <button style={{
          background: bundle.highlight ? bundle.color : `${bundle.color}15`,
          border: bundle.highlight ? 'none' : `1px solid ${bundle.color}44`,
          color: bundle.highlight ? '#000' : bundle.color,
          padding: '6px 16px',
          borderRadius: '4px',
          fontSize: '0.75rem',
          fontWeight: 700,
          cursor: 'pointer',
        }}>
          {bundle.highlight ? 'Get Started' : 'Try 24H Free'}
        </button>
      </div>
    </div>
  );
}

function OrgPlanRow({ plans, label, color, extraFeatures }: { plans: OrgPlan[]; label: string; color: string; extraFeatures?: string[] }) {
  return (
    <div style={{
      ...cardBase,
      borderColor: `${color}33`,
      padding: '1.25rem 1.5rem',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
        <div>
          <div style={{ fontSize: '1rem', fontWeight: 700, color }}>{label}</div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '0.15rem' }}>Seat-based plans &mdash; heavy features for assigned users</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${plans.length}, 1fr)`, gap: '0.75rem', marginBottom: '1rem' }}>
        {plans.map(plan => (
          <div key={plan.name} style={{
            background: plan.highlight ? `${color}0a` : 'var(--bg-primary)',
            border: `1px solid ${plan.highlight ? `${color}44` : 'var(--border-color)'}`,
            borderRadius: '6px',
            padding: '1rem',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: '0.8rem', fontWeight: 700, color: plan.highlight ? color : 'var(--text-primary)', marginBottom: '0.25rem' }}>
              {plan.name}
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1.2 }}>
              {plan.seats}
            </div>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>heavy seats</div>
            <div style={{ fontSize: '0.95rem', fontWeight: 700, color: plan.highlight ? color : 'var(--text-primary)' }}>
              {plan.price}
            </div>
            <div style={{ fontSize: '0.6rem', color: 'var(--text-secondary)' }}>/ 30 days</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem', fontSize: '0.7rem' }}>
        <div>
          <div style={{ color: '#3fb950', fontWeight: 600, marginBottom: '0.25rem' }}>All Members</div>
          <div style={{ color: 'var(--text-secondary)' }}>Intel modules, Character Suite, Market Analysis</div>
        </div>
        <div>
          <div style={{ color: '#d29922', fontWeight: 600, marginBottom: '0.25rem' }}>Seated Users</div>
          <div style={{ color: 'var(--text-secondary)' }}>Entity Deep-Dive (all types, unlimited), Battle Analysis</div>
        </div>
        <div>
          <div style={{ color: '#f85149', fontWeight: 600, marginBottom: '0.25rem' }}>Directors / Officers</div>
          <div style={{ color: 'var(--text-secondary)' }}>
            {extraFeatures
              ? extraFeatures.join(', ')
              : 'Finance, HR, SRP, PAP, Timers, Contracts, Roles'}
          </div>
        </div>
      </div>
    </div>
  );
}

function EntityTrialButton({ entityTab, color, isOwned, isLoggedIn, onLogin, onTrialActivated }: {
  entityTab: 'corp' | 'alliance' | 'powerbloc';
  color: string;
  isOwned: boolean;
  isLoggedIn: boolean;
  onLogin: () => void;
  onTrialActivated: () => void;
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const moduleId = `${entityTab === 'corp' ? 'corp' : entityTab === 'alliance' ? 'alliance' : 'powerbloc'}_intel`;

  const handleTrial = async () => {
    if (!isLoggedIn) { onLogin(); return; }
    setLoading(true);
    setError(null);
    try {
      await moduleApi.activateTrial(moduleId);
      setSuccess(true);
      onTrialActivated();
    } catch (err: unknown) {
      const e = err as { response?: { status?: number } };
      if (e?.response?.status === 409) setError('Trial already used');
      else setError('Activation failed');
    } finally {
      setLoading(false);
    }
  };

  if (isOwned) {
    return (
      <div style={{
        marginTop: '0.75rem',
        background: 'rgba(63,185,80,0.1)',
        border: '1px solid rgba(63,185,80,0.3)',
        padding: '6px 0',
        borderRadius: '4px',
        fontSize: '0.75rem',
        fontWeight: 600,
        color: '#3fb950',
        textAlign: 'center',
      }}>
        &#10003; Active
      </div>
    );
  }

  if (success) {
    return (
      <div style={{
        marginTop: '0.75rem',
        background: 'rgba(63,185,80,0.1)',
        border: '1px solid rgba(63,185,80,0.3)',
        padding: '6px 0',
        borderRadius: '4px',
        fontSize: '0.75rem',
        fontWeight: 600,
        color: '#3fb950',
        textAlign: 'center',
      }}>
        Trial Active (24H)
      </div>
    );
  }

  return (
    <>
      {error && <div style={{ fontSize: '0.7rem', color: '#f85149', marginTop: '0.3rem', textAlign: 'center' }}>{error}</div>}
      <button
        onClick={handleTrial}
        disabled={loading}
        style={{
          marginTop: '0.75rem',
          background: `${color}15`,
          border: `1px solid ${color}44`,
          color,
          padding: '6px 0',
          borderRadius: '4px',
          fontSize: '0.75rem',
          fontWeight: 600,
          cursor: loading ? 'wait' : 'pointer',
          width: '100%',
          opacity: loading ? 0.6 : 1,
        }}
      >
        {loading ? 'Activating...' : isLoggedIn ? 'Try 24H Free' : 'Sign In to Try'}
      </button>
    </>
  );
}

// --- Main Component ---

export function Pricing() {
  const { isLoggedIn, login, refresh } = useAuth();
  const { hasModule } = useModules();
  const [activeEntityTab, setActiveEntityTab] = useState<'corp' | 'alliance' | 'powerbloc'>('corp');

  const entityColors = { corp: '#ffcc00', alliance: '#ff4444', powerbloc: '#a855f7' };
  const entityLabels = { corp: 'Corporation', alliance: 'Alliance', powerbloc: 'PowerBloc' };
  const entityTabs = { corp: '8 tabs, 7D\u201390D', alliance: '9 tabs, 24H\u201330D', powerbloc: '9 tabs, 24H\u201330D' };

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: '0 1rem' }}>
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
        <h1 style={{ fontSize: '2rem', fontWeight: 700, marginBottom: '0.4rem' }}>
          Choose Your Intel
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '1rem', margin: 0 }}>
          Pay only for what you need. Every module includes a free 24-hour trial.
        </p>
      </div>

      {/* Free Base */}
      <div style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: '8px',
        padding: '1.25rem 1.5rem',
        marginBottom: '2rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.3rem' }}>
            <span style={{ fontSize: '0.95rem', fontWeight: 700, color: '#8b949e' }}>FREE</span>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>&mdash; always included</span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', fontSize: '0.75rem', color: 'var(--text-primary)' }}>
            {['Homepage LiveMap', 'Market (Jita)', 'Ships Database', 'Entity Overviews', 'Intel Previews (1H, Top 5)', 'Character Card'].map(f => (
              <span key={f} style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                <span style={{ color: '#8b949e' }}>&#10003;</span> {f}
              </span>
            ))}
          </div>
        </div>
        {!isLoggedIn && (
          <button onClick={login} style={{
            background: '#8b949e22',
            border: '1px solid #8b949e44',
            color: '#8b949e',
            padding: '8px 20px',
            borderRadius: '4px',
            fontSize: '0.8rem',
            fontWeight: 600,
            cursor: 'pointer',
            whiteSpace: 'nowrap',
          }}>
            Sign In with EVE
          </button>
        )}
      </div>

      {/* Intel Modules */}
      <div style={sectionTitle}>Intel Modules &mdash; 100M ISK each</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '0.75rem', marginBottom: '2rem' }}>
        {INTEL_MODULES.map(mod => (
          <ModuleCard key={mod.id} mod={mod} isOwned={hasModule(mod.id)} isLoggedIn={isLoggedIn} onLogin={login} onTrialActivated={refresh} />
        ))}
      </div>

      {/* Personal Modules */}
      <div style={sectionTitle}>Personal Modules</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.75rem', marginBottom: '2rem' }}>
        {PERSONAL_MODULES.map(mod => (
          <ModuleCard key={mod.id} mod={mod} isOwned={hasModule(mod.id)} isLoggedIn={isLoggedIn} onLogin={login} onTrialActivated={refresh} />
        ))}
      </div>

      {/* Entity Deep-Dive */}
      <div style={sectionTitle}>Entity Deep-Dive &mdash; tiered pricing</div>
      <div style={{
        ...cardBase,
        padding: '1.25rem 1.5rem',
        marginBottom: '2rem',
      }}>
        {/* Entity type tabs */}
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
          {(['corp', 'alliance', 'powerbloc'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveEntityTab(tab)}
              style={{
                background: activeEntityTab === tab ? `${entityColors[tab]}15` : 'transparent',
                border: `1px solid ${activeEntityTab === tab ? entityColors[tab] : 'var(--border-color)'}`,
                color: activeEntityTab === tab ? entityColors[tab] : 'var(--text-secondary)',
                padding: '6px 16px',
                borderRadius: '4px',
                fontSize: '0.8rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              {entityLabels[tab]}
            </button>
          ))}
        </div>

        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
          {entityLabels[activeEntityTab]} Intel &mdash; {entityTabs[activeEntityTab]}. All tabs: Offensive, Defensive, Capitals, Geography, Wormhole, Hunting + more.
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem' }}>
          {ENTITY_TIERS.map((tier, i) => {
            const price = activeEntityTab === 'corp' ? tier.corp : activeEntityTab === 'alliance' ? tier.alliance : tier.powerbloc;
            const isUnlimited = tier.scope === 'Unlimited';
            const col = entityColors[activeEntityTab];
            return (
              <div key={tier.scope} style={{
                background: isUnlimited ? `${col}08` : 'var(--bg-primary)',
                border: `1px solid ${isUnlimited ? `${col}44` : 'var(--border-color)'}`,
                borderRadius: '6px',
                padding: '1rem',
                textAlign: 'center',
              }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: isUnlimited ? col : 'var(--text-secondary)', marginBottom: '0.25rem' }}>
                  {tier.scope}
                </div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  {price}
                </div>
                <div style={{ fontSize: '0.6rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>/ 30 days</div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
                  {i === 0 ? 'Switch once per 7 days' : i === 1 ? 'Any 5 simultaneously' : 'No restrictions'}
                </div>
              </div>
            );
          })}
        </div>

        <EntityTrialButton
          entityTab={activeEntityTab}
          color={entityColors[activeEntityTab]}
          isOwned={hasModule(`${activeEntityTab === 'corp' ? 'corp' : activeEntityTab === 'alliance' ? 'alliance' : 'powerbloc'}_intel`)}
          isLoggedIn={isLoggedIn}
          onLogin={login}
          onTrialActivated={refresh}
        />
      </div>

      {/* Bundles */}
      <div style={sectionTitle}>Bundles &mdash; save up to 40%</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem', marginBottom: '2.5rem' }}>
        {BUNDLES.map(b => <BundleCard key={b.name} bundle={b} />)}
      </div>

      {/* Organization Plans */}
      <div style={sectionTitle}>Organization Plans &mdash; seat-based</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1rem' }}>
        <OrgPlanRow plans={CORP_PLANS} label="Corporation" color="#ffcc00" />
        <OrgPlanRow
          plans={ALLIANCE_PLANS}
          label="Alliance"
          color="#ff4444"
          extraFeatures={['Everything in Corp +', 'Sov, Skyhook, Metenox, MCP/AI, Discord']}
        />
      </div>

      {/* Coalition */}
      <div style={{
        ...cardBase,
        borderColor: '#a855f733',
        padding: '1.25rem 1.5rem',
        marginBottom: '2rem',
        display: 'flex',
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div>
          <div style={{ fontSize: '1rem', fontWeight: 700, color: '#a855f7' }}>Coalition</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
            Dedicated instance &middot; Unlimited seats &middot; Custom integrations &middot; Priority support
          </div>
        </div>
        <button style={{
          background: '#a855f722',
          border: '1px solid #a855f744',
          color: '#a855f7',
          padding: '8px 20px',
          borderRadius: '4px',
          fontSize: '0.8rem',
          fontWeight: 600,
          cursor: 'pointer',
          whiteSpace: 'nowrap',
        }}>
          Contact Us
        </button>
      </div>

      {/* Payment Info */}
      <div style={{
        textAlign: 'center',
        padding: '1.5rem',
        background: 'var(--bg-secondary)',
        borderRadius: '8px',
        border: '1px solid var(--border-color)',
        marginBottom: '2rem',
      }}>
        <h3 style={{ marginBottom: '0.5rem', fontSize: '1rem' }}>How Payment Works</h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', maxWidth: 600, margin: '0 auto', lineHeight: 1.5 }}>
          All payments are made in ISK. Select a module or plan, receive a unique payment code,
          and transfer ISK to our holding character with the code as reason. Your subscription
          activates automatically within minutes. Every module includes a free 24-hour trial.
        </p>
      </div>

      {/* FAQ */}
      <div style={{ marginBottom: '2rem' }}>
        <div style={{ ...sectionTitle, textAlign: 'center', borderBottom: 'none', paddingBottom: 0 }}>
          Frequently Asked Questions
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.5rem', marginTop: '1rem' }}>
          {[
            { q: 'How do ISK payments work?', a: 'Select a module or plan, receive a unique PAY-XXXXX code, and send ISK to our holding character with the code as reason. Subscriptions activate automatically within minutes.' },
            { q: 'Can I try modules before paying?', a: 'Every module includes a free 24-hour trial. Click "Try 24H Free" on any module card above — no ISK required.' },
            { q: 'What happens when my subscription expires?', a: 'You get a 7-day warning and a 3-day grace period with continued access. After that, features revert to your previous tier. No data is lost.' },
            { q: 'Can I switch plans?', a: 'Upgrade anytime — your remaining time is prorated. Downgrades take effect at the end of your current billing period.' },
          ].map(item => (
            <div key={item.q} style={{
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              padding: '0.85rem 1rem',
            }}>
              <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.3rem' }}>
                {item.q}
              </div>
              <p style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', lineHeight: 1.5, margin: 0 }}>
                {item.a}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* How It Works CTA */}
      <div style={{
        textAlign: 'center',
        padding: '1.5rem',
        marginBottom: '1rem',
      }}>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '0.75rem' }}>
          Want to learn more about the platform?
        </p>
        <Link
          to="/how-it-works"
          style={{
            display: 'inline-block',
            padding: '10px 24px',
            background: 'rgba(255,255,255,0.05)',
            border: '1px solid rgba(255,255,255,0.15)',
            borderRadius: '6px',
            color: 'var(--text-primary)',
            fontSize: '0.85rem',
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
