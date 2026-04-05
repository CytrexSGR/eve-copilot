interface SovCampaign {
  system_name: string;
  structure_type: string;
  defender: string | null;
  score: number | null;
  adm: number | null;
}

interface StrategicContext {
  battle_id: number;
  system_sov: { alliance_id: number; alliance_name: string } | null;
  active_campaigns: SovCampaign[];
  constellation_campaigns: number;
  strategic_note: string | null;
}

interface BattleSovContextProps {
  context: StrategicContext | null;
}

export function BattleSovContext({ context }: BattleSovContextProps) {
  if (!context || (context.active_campaigns.length === 0 && !context.strategic_note)) return null;

  const hasCampaigns = context.active_campaigns.length > 0;
  const borderColor = hasCampaigns ? '#f85149' : '#d29922';

  return (
    <div style={{
      background: `${borderColor}10`,
      borderRadius: '6px',
      border: `1px solid ${borderColor}40`,
      padding: '0.4rem 1rem',
      marginBottom: '0.75rem',
      fontSize: '0.7rem',
    }}>
      {/* Campaign alerts */}
      {hasCampaigns && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
          {context.active_campaigns.map((campaign, idx) => (
            <div key={idx} style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              flexWrap: 'wrap',
            }}>
              <span style={{
                animation: 'pulse 1.5s ease-in-out infinite',
                fontSize: '0.75rem',
              }}>
                {'\u26A0'}
              </span>

              <span style={{
                padding: '0.1rem 0.3rem',
                borderRadius: '2px',
                background: '#f8514920',
                color: '#f85149',
                fontSize: '0.6rem',
                fontWeight: 700,
              }}>
                SOV CONTESTED
              </span>

              <span style={{ color: '#c9d1d9', fontWeight: 600 }}>
                {campaign.system_name}
              </span>

              <span style={{
                padding: '0.1rem 0.3rem',
                borderRadius: '2px',
                background: 'rgba(255,255,255,0.08)',
                color: '#8b949e',
                fontSize: '0.6rem',
                fontWeight: 600,
              }}>
                {campaign.structure_type}
              </span>

              {campaign.defender && (
                <span style={{ color: '#8b949e' }}>
                  Defender: <span style={{ color: '#a855f7' }}>{campaign.defender}</span>
                </span>
              )}

              {campaign.score !== null && (
                <span>
                  <span style={{ color: '#6e7681' }}>Score </span>
                  <span style={{
                    color: campaign.score > 50 ? '#3fb950' : campaign.score > 30 ? '#d29922' : '#f85149',
                    fontWeight: 700,
                    fontFamily: 'monospace',
                  }}>
                    {campaign.score.toFixed(0)}%
                  </span>
                </span>
              )}

              {campaign.adm !== null && (
                <span>
                  <span style={{ color: '#6e7681' }}>ADM </span>
                  <span style={{
                    color: campaign.adm < 2 ? '#f85149' : campaign.adm < 4 ? '#d29922' : '#3fb950',
                    fontWeight: 700,
                    fontFamily: 'monospace',
                  }}>
                    {campaign.adm.toFixed(1)}
                  </span>
                </span>
              )}
            </div>
          ))}

          {context.constellation_campaigns > 0 && (
            <span style={{ color: '#6e7681', fontSize: '0.6rem', marginLeft: '1.5rem' }}>
              +{context.constellation_campaigns} more campaign{context.constellation_campaigns > 1 ? 's' : ''} in constellation
            </span>
          )}
        </div>
      )}

      {/* Constellation-only note (no system campaigns) */}
      {!hasCampaigns && context.strategic_note && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ color: '#d29922' }}>{'\u26A0'}</span>
          <span style={{ color: '#d29922' }}>{context.strategic_note}</span>
        </div>
      )}
    </div>
  );
}
