interface PBHuntingViewProps {
  leaderId: number;
  days: number;
}

export function PBHuntingView({ leaderId, days }: PBHuntingViewProps) {
  return (
    <div style={{ padding: '2rem', textAlign: 'center', color: '#8b949e' }}>
      <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🔍</div>
      <div style={{ fontSize: '1rem', fontWeight: 700, color: '#e6edf3', marginBottom: '0.5rem' }}>
        HUNTING INTELLIGENCE
      </div>
      <div style={{ fontSize: '0.75rem' }}>
        Target acquisition &amp; hunting patterns coming soon. PowerBloc {leaderId}, {days}d window.
      </div>
    </div>
  );
}
