import { Suspense, type ReactNode } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from './lib/queryClient';
import { lazyRetry } from './lib/lazyRetry';
import { Layout } from './components/Layout';
import { ErrorBoundary } from './components/ErrorBoundary';
import { AuthProvider } from './context/AuthContext';
import { PilotIntelProvider } from './context/PilotIntelContext';
import { useAuth } from './hooks/useAuth';
import { Home } from './pages/Home';
import './App.css';

// Lazy load pages with automatic retry on chunk loading failure
const BattleReport = lazyRetry(() => import('./pages/BattleReport').then(m => ({ default: m.BattleReport })));
const BattleMap = lazyRetry(() => import('./pages/BattleMap2D').then(m => ({ default: m.BattleMap2D })));
const BattleDetail = lazyRetry(() => import('./pages/BattleDetail').then(m => ({ default: m.BattleDetail })));
const WarEconomy = lazyRetry(() => import('./pages/WarEconomy').then(m => ({ default: m.WarEconomy })));
const Impressum = lazyRetry(() => import('./pages/Impressum').then(m => ({ default: m.Impressum })));
const Datenschutz = lazyRetry(() => import('./pages/Datenschutz').then(m => ({ default: m.Datenschutz })));
const SupplyChain = lazyRetry(() => import('./pages/SupplyChain'));
const Doctrines = lazyRetry(() => import('./pages/Doctrines').then(m => ({ default: m.Doctrines })));
const NotFound = lazyRetry(() => import('./pages/NotFound').then(m => ({ default: m.NotFound })));
const Ectmap = lazyRetry(() => import('./pages/Ectmap').then(m => ({ default: m.Ectmap })));
const ConflictDetail = lazyRetry(() => import('./pages/ConflictDetail').then(m => ({ default: m.ConflictDetail })));
const SystemDetail = lazyRetry(() => import('./pages/SystemDetail').then(m => ({ default: m.SystemDetail })));
const RouteDetail = lazyRetry(() => import('./pages/RouteDetail').then(m => ({ default: m.RouteDetail })));
const WormholeIntel = lazyRetry(() => import('./pages/WormholeIntel').then(m => ({ default: m.WormholeIntel })));
const AllianceDetail = lazyRetry(() => import('./pages/AllianceDetail').then(m => ({ default: m.AllianceDetail })));
const PowerBlocDetail = lazyRetry(() => import('./pages/PowerBlocDetail'));
const CorporationDetail = lazyRetry(() => import('./pages/CorporationDetail').then(m => ({ default: m.CorporationDetail })));
const AuthCallback = lazyRetry(() => import('./pages/AuthCallback').then(m => ({ default: m.AuthCallback })));
const Pricing = lazyRetry(() => import('./pages/Pricing').then(m => ({ default: m.Pricing })));
const Subscription = lazyRetry(() => import('./pages/Subscription').then(m => ({ default: m.Subscription })));
const Account = lazyRetry(() => import('./pages/Account').then(m => ({ default: m.Account })));
const Market = lazyRetry(() => import('./pages/Market').then(m => ({ default: m.Market })));
const Production = lazyRetry(() => import('./pages/Production').then(m => ({ default: m.Production })));
const PlanetaryIndustry = lazyRetry(() => import('./pages/PlanetaryIndustry').then(m => ({ default: m.PlanetaryIndustry })));
const PIAdvisorDetail = lazyRetry(() => import('./pages/PIAdvisorDetail').then(m => ({ default: m.PIAdvisorDetail })));
const ProjectList = lazyRetry(() => import('./pages/ProjectList').then(m => ({ default: m.ProjectList })));
const ProjectDetailPage = lazyRetry(() => import('./pages/ProjectDetail').then(m => ({ default: m.ProjectDetail })));
const Characters = lazyRetry(() => import('./pages/Characters').then(m => ({ default: m.Characters })));
const Fittings = lazyRetry(() => import('./pages/Fittings').then(m => ({ default: m.Fittings })));
const FittingDetail = lazyRetry(() => import('./pages/FittingDetail').then(m => ({ default: m.FittingDetail })));
const FittingEditor = lazyRetry(() => import('./pages/FittingEditor').then(m => ({ default: m.FittingEditor })));
const FittingComparison = lazyRetry(() => import('./pages/FittingComparison').then(m => ({ default: m.FittingComparison })));
const Navigation = lazyRetry(() => import('./pages/Navigation').then(m => ({ default: m.Navigation })));
const Shopping = lazyRetry(() => import('./pages/Shopping').then(m => ({ default: m.Shopping })));
const Intel = lazyRetry(() => import('./pages/Intel').then(m => ({ default: m.Intel })));
const CorpDashboard = lazyRetry(() => import('./pages/CorpDashboard').then(m => ({ default: m.CorpDashboard })));
const CorpFinance = lazyRetry(() => import('./pages/CorpFinance').then(m => ({ default: m.CorpFinance })));
const CorpHR = lazyRetry(() => import('./pages/CorpHR').then(m => ({ default: m.CorpHR })));
const CorpSRP = lazyRetry(() => import('./pages/CorpSRP').then(m => ({ default: m.CorpSRP })));
const CorpFleet = lazyRetry(() => import('./pages/CorpFleet').then(m => ({ default: m.CorpFleet })));
const CorpTimers = lazyRetry(() => import('./pages/CorpTimers').then(m => ({ default: m.CorpTimers })));
const CorpTools = lazyRetry(() => import('./pages/CorpTools').then(m => ({ default: m.CorpTools })));
const CorpDiplo = lazyRetry(() => import('./pages/CorpDiplo').then(m => ({ default: m.CorpDiplo })));
const CorpMembers = lazyRetry(() => import('./pages/CorpMembers'));
const Dashboard = lazyRetry(() => import('./pages/Dashboard').then(m => ({ default: m.Dashboard })));
const HowItWorks = lazyRetry(() => import('./pages/HowItWorks').then(m => ({ default: m.HowItWorks })));

// Loading fallback component
const PageLoader = () => (
  <div style={{
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '400px',
    color: 'var(--text-secondary)'
  }}>
    <div className="skeleton" style={{ width: '100%', height: '400px' }} />
  </div>
);

// Require ESI login for all app content
function RequireAuth({ children }: { children: ReactNode }) {
  const { isLoggedIn, isLoading, login } = useAuth();

  if (isLoading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        background: '#0d1117',
        color: '#8b949e',
        fontSize: '0.9rem',
      }}>
        Authenticating...
      </div>
    );
  }

  if (!isLoggedIn) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        background: '#0d1117',
        gap: '1.5rem',
      }}>
        <div style={{
          fontSize: '2rem',
          fontWeight: 700,
          color: '#e6edf3',
          letterSpacing: '0.02em',
        }}>
          Infinimind Intelligence
        </div>
        <div style={{
          color: '#8b949e',
          fontSize: '0.9rem',
        }}>
          EVE Online Real-time Intelligence Platform
        </div>
        <button
          onClick={() => login()}
          style={{
            marginTop: '1rem',
            padding: '12px 32px',
            background: 'linear-gradient(135deg, #1a3a5c, #0d2137)',
            border: '1px solid #30363d',
            borderRadius: '6px',
            color: '#e6edf3',
            fontSize: '1rem',
            fontWeight: 600,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          Login with EVE Online
        </button>
        <div style={{
          color: '#484f58',
          fontSize: '0.75rem',
          marginTop: '0.5rem',
        }}>
          Requires EVE SSO authentication
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <PilotIntelProvider>
        <BrowserRouter>
          <Routes>
            {/* Public routes — no auth required */}
            <Route path="/auth/callback" element={<ErrorBoundary><Suspense fallback={<PageLoader />}><AuthCallback /></Suspense></ErrorBoundary>} />
            <Route path="/impressum" element={<Layout><ErrorBoundary><Suspense fallback={<PageLoader />}><Impressum /></Suspense></ErrorBoundary></Layout>} />
            <Route path="/datenschutz" element={<Layout><ErrorBoundary><Suspense fallback={<PageLoader />}><Datenschutz /></Suspense></ErrorBoundary></Layout>} />

            {/* All other routes require ESI login */}
            <Route path="*" element={
              <RequireAuth>
                <Layout>
                  <ErrorBoundary>
                  <Suspense fallback={<PageLoader />}>
                    <Routes>
                      <Route path="/" element={<Home />} />
                      <Route path="/battle-report" element={<BattleReport />} />
                      <Route path="/battle-map" element={<BattleMap />} />
                      <Route path="/battle/:id" element={<BattleDetail />} />
                      <Route path="/conflicts/:conflictId" element={<ConflictDetail />} />
                      <Route path="/war-economy" element={<WarEconomy />} />
                      <Route path="/wormhole" element={<WormholeIntel />} />
                      <Route path="/alliance/:allianceId" element={<AllianceDetail />} />
                      <Route path="/powerbloc/:leaderAllianceId" element={<PowerBlocDetail />} />
                      <Route path="/corporation/:corpId" element={<CorporationDetail />} />
                      <Route path="/alliance-wars" element={<Navigate to="/battle-report" replace />} />
                      <Route path="/trade-routes" element={<Navigate to="/war-economy#routes" replace />} />
                      <Route path="/supply-chain" element={<SupplyChain />} />
                      <Route path="/supply-chain/:allianceId" element={<SupplyChain />} />
                      <Route path="/doctrines" element={<Doctrines />} />
                      <Route path="/ectmap" element={<Ectmap />} />
                      <Route path="/system/:systemId" element={<SystemDetail />} />
                      <Route path="/route/:origin/:destination" element={<RouteDetail />} />
                      <Route path="/pricing" element={<Pricing />} />
                      <Route path="/subscription" element={<Subscription />} />
                      <Route path="/account" element={<Account />} />
                      <Route path="/market" element={<Market />} />
                      <Route path="/production" element={<Production />} />
                      <Route path="/production/projects" element={<ProjectList />} />
                      <Route path="/production/projects/:projectId" element={<ProjectDetailPage />} />
                      <Route path="/production/pi" element={<PlanetaryIndustry />} />
                      <Route path="/production/pi/:typeId" element={<PIAdvisorDetail />} />
                      <Route path="/characters" element={<Characters />} />
                      <Route path="/fittings" element={<Fittings />} />
                      <Route path="/fittings/compare" element={<FittingComparison />} />
                      <Route path="/fittings/new" element={<FittingEditor />} />
                      <Route path="/fittings/esi/:fittingId" element={<FittingDetail />} />
                      <Route path="/fittings/custom/:fittingId" element={<FittingDetail />} />
                      <Route path="/navigation" element={<Navigation />} />
                      <Route path="/shopping" element={<Shopping />} />
                      <Route path="/intel" element={<Intel />} />
                      <Route path="/corp" element={<CorpDashboard />} />
                      <Route path="/corp/finance" element={<CorpFinance />} />
                      <Route path="/corp/hr" element={<CorpHR />} />
                      <Route path="/corp/srp" element={<CorpSRP />} />
                      <Route path="/corp/fleet" element={<CorpFleet />} />
                      <Route path="/corp/timers" element={<CorpTimers />} />
                      <Route path="/corp/tools" element={<CorpTools />} />
                      <Route path="/corp/diplo" element={<CorpDiplo />} />
                      <Route path="/corp/members" element={<CorpMembers />} />
                      <Route path="/dashboard" element={<Dashboard />} />
                      <Route path="/how-it-works" element={<HowItWorks />} />
                      <Route path="*" element={<NotFound />} />
                    </Routes>
                  </Suspense>
                  </ErrorBoundary>
                </Layout>
              </RequireAuth>
            } />
          </Routes>
        </BrowserRouter>
        </PilotIntelProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
