import { PIChainPlanner } from '../components/production/PIChainPlanner';

export function PlanetaryIndustry() {
  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '1.5rem 1rem' }}>
      <div style={{ marginBottom: '1rem' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, margin: '0 0 0.25rem 0' }}>
          Planetary Industry
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: 0 }}>
          PI chain planning, character assignment, and item PI analysis
        </p>
      </div>

      <PIChainPlanner />
    </div>
  );
}
