import type { StrategicBriefing, AllianceWarsAnalysis } from '../../types/reports';

interface IntelligenceTabProps {
  briefing: StrategicBriefing | null;
  briefingLoading: boolean;
  allianceAnalysis: AllianceWarsAnalysis | null;
  allianceLoading: boolean;
}

const sectionStyle = {
  background: 'linear-gradient(135deg, rgba(15,20,30,0.95) 0%, rgba(20,25,35,0.9) 100%)',
  borderRadius: '12px',
  border: '1px solid rgba(100, 150, 255, 0.1)',
  padding: '1.5rem',
  marginBottom: '1.5rem'
};

export function IntelligenceTab({
  briefing,
  briefingLoading,
  allianceAnalysis,
  allianceLoading
}: IntelligenceTabProps) {
  return (
    <>
      {/* Strategic Briefing */}
      <div style={{
        ...sectionStyle,
        borderLeft: '3px solid #a855f7'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
          <span style={{ fontSize: '1.25rem' }}>🎖️</span>
          <div>
            <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#a855f7' }}>Strategic Intelligence Briefing</h2>
            <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.7rem', margin: 0, marginTop: '0.25rem' }}>
              AI-powered analysis for alliance leadership
              {briefing?.generated_at && <span> • {new Date(briefing.generated_at).toLocaleTimeString()}</span>}
            </p>
          </div>
        </div>
        {briefingLoading ? (
          <div className="skeleton" style={{ height: '100px' }} />
        ) : briefing?.error ? (
          <div style={{ padding: '1rem', background: 'rgba(255, 68, 68, 0.1)', borderRadius: '8px', border: '1px solid rgba(255, 68, 68, 0.3)', color: '#ff4444' }}>
            {briefing.error}
          </div>
        ) : briefing ? (
          <div>
            {briefing.alerts && briefing.alerts.length > 0 && (
              <div style={{ marginBottom: '1.25rem' }}>
                <div style={{ fontSize: '0.7rem', color: '#ff4444', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.75rem' }}>
                  ⚠️ Priority Alerts ({briefing.alerts.length})
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.75rem' }}>
                  {briefing.alerts.map((alert, idx) => (
                    <div key={idx} style={{
                      padding: '1rem',
                      background: 'linear-gradient(135deg, rgba(255,68,68,0.15) 0%, rgba(255,68,68,0.05) 100%)',
                      border: '1px solid rgba(255,68,68,0.3)',
                      borderLeft: '4px solid #ff4444',
                      borderRadius: '8px',
                      fontSize: '0.85rem',
                      color: 'rgba(255,255,255,0.9)',
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '0.75rem'
                    }}>
                      <span style={{
                        fontSize: '1.25rem',
                        background: 'rgba(255,68,68,0.2)',
                        borderRadius: '50%',
                        width: '32px',
                        height: '32px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0
                      }}>🚨</span>
                      <span>{alert}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            <div style={{
              padding: '1rem',
              background: 'rgba(0,0,0,0.2)',
              borderRadius: '8px',
              marginBottom: '1rem',
              lineHeight: '1.7',
              border: '1px solid rgba(255,255,255,0.05)'
            }}>
              {briefing.briefing.split('\n').map((p, idx) => (
                <p key={idx} style={{ marginBottom: '0.75rem', color: 'rgba(255,255,255,0.8)', fontSize: '0.9rem' }}>{p}</p>
              ))}
            </div>
            {briefing.highlights && briefing.highlights.length > 0 && (
              <div style={{ marginTop: '1.25rem' }}>
                <div style={{ fontSize: '0.7rem', color: '#00d4ff', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.75rem' }}>
                  🎯 Key Highlights
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '0.75rem' }}>
                  {briefing.highlights.map((h, idx) => (
                    <div key={idx} style={{
                      padding: '1rem',
                      background: 'linear-gradient(135deg, rgba(0,212,255,0.1) 0%, rgba(0,212,255,0.02) 100%)',
                      borderRadius: '8px',
                      borderLeft: '3px solid #00d4ff',
                      fontSize: '0.85rem',
                      color: 'rgba(255,255,255,0.8)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.75rem'
                    }}>
                      <span style={{ color: '#00d4ff', fontSize: '0.9rem' }}>→</span>
                      {h}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : null}
      </div>

      {/* Alliance Wars Analysis */}
      <div style={{
        ...sectionStyle,
        borderLeft: '3px solid #00ff88',
        marginBottom: 0
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
          <span style={{ fontSize: '1.25rem' }}>🤖</span>
          <div>
            <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#00ff88' }}>Alliance Warfare Analysis</h2>
            <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.7rem', margin: 0, marginTop: '0.25rem' }}>
              Coalition dynamics and conflict trends
              {allianceAnalysis?.generated_at && <span> • {new Date(allianceAnalysis.generated_at).toLocaleTimeString()}</span>}
            </p>
          </div>
        </div>
        {allianceLoading ? (
          <div className="skeleton" style={{ height: '100px' }} />
        ) : allianceAnalysis?.error ? (
          <div style={{ padding: '1rem', background: 'rgba(255, 68, 68, 0.1)', borderRadius: '8px', border: '1px solid rgba(255, 68, 68, 0.3)', color: '#ff4444' }}>
            {allianceAnalysis.error}
          </div>
        ) : allianceAnalysis ? (
          <div>
            <div style={{
              padding: '1rem',
              background: 'rgba(0,0,0,0.2)',
              borderRadius: '8px',
              marginBottom: '1rem',
              lineHeight: '1.7',
              border: '1px solid rgba(255,255,255,0.05)'
            }}>
              {allianceAnalysis.summary.split('\n').map((p, idx) => (
                <p key={idx} style={{ marginBottom: '0.75rem', color: 'rgba(255,255,255,0.8)', fontSize: '0.9rem' }}>{p}</p>
              ))}
            </div>
            {allianceAnalysis.insights && allianceAnalysis.insights.length > 0 && (
              <div style={{ marginBottom: '1rem' }}>
                <h3 style={{ fontSize: '0.7rem', marginBottom: '0.75rem', color: '#00d4ff', textTransform: 'uppercase', letterSpacing: '0.05em' }}>📊 Key Insights</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.5rem' }}>
                  {allianceAnalysis.insights.map((insight, idx) => (
                    <div key={idx} style={{
                      padding: '0.75rem 1rem',
                      background: 'rgba(0, 212, 255, 0.05)',
                      borderRadius: '6px',
                      borderLeft: '3px solid #00d4ff',
                      fontSize: '0.85rem',
                      color: 'rgba(255,255,255,0.8)'
                    }}>
                      {insight}
                    </div>
                  ))}
                </div>
              </div>
            )}
            {allianceAnalysis.trends && allianceAnalysis.trends.length > 0 && (
              <div>
                <h3 style={{ fontSize: '0.7rem', marginBottom: '0.75rem', color: '#00ff88', textTransform: 'uppercase', letterSpacing: '0.05em' }}>📈 Trends</h3>
                {allianceAnalysis.trends.map((trend, idx) => (
                  <div key={idx} style={{
                    padding: '0.75rem 1rem',
                    background: 'rgba(0, 255, 136, 0.05)',
                    borderRadius: '6px',
                    borderLeft: '3px solid #00ff88',
                    marginBottom: '0.5rem',
                    fontSize: '0.85rem',
                    color: 'rgba(255,255,255,0.8)'
                  }}>
                    {trend}
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : null}
      </div>
    </>
  );
}
