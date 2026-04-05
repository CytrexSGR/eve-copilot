import type { WarEconomyAnalysis } from '../../types/reports';

interface IntelTabProps {
  analysis: WarEconomyAnalysis | null;
  loading: boolean;
}

export function IntelTab({ analysis, loading }: IntelTabProps) {
  return (
    <div style={{
      background: 'linear-gradient(135deg, rgba(15,20,30,0.95) 0%, rgba(20,25,35,0.9) 100%)',
      borderRadius: '12px',
      border: '1px solid rgba(100, 150, 255, 0.1)',
      padding: '1.5rem'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={{ fontSize: '1.25rem' }}>🤖</span>
          <div>
            <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#00d4ff' }}>Market Intelligence Briefing</h2>
            <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.75rem', margin: 0 }}>
              AI-generated analysis of market conditions and trading opportunities
            </p>
          </div>
        </div>
        {analysis && (
          <span style={{
            fontSize: '0.7rem',
            color: 'rgba(255,255,255,0.4)',
            padding: '0.25rem 0.5rem',
            background: 'rgba(0,0,0,0.3)',
            borderRadius: '4px'
          }}>
            Updated: {new Date(analysis.generated_at).toLocaleTimeString()}
          </span>
        )}
      </div>

      {loading ? (
        <div className="skeleton" style={{ height: '200px' }} />
      ) : analysis?.error ? (
        <div style={{ padding: '2rem', textAlign: 'center', color: '#ffcc00' }}>
          Analysis temporarily unavailable.
        </div>
      ) : analysis ? (
        <div style={{ display: 'grid', gap: '1.5rem' }}>
          {/* Summary */}
          <AnalysisSection icon="" title="Summary" color="#00d4ff">
            <p style={{ color: 'rgba(255,255,255,0.8)', lineHeight: 1.7, whiteSpace: 'pre-wrap', margin: 0 }}>
              {analysis.summary}
            </p>
          </AnalysisSection>

          {/* Doctrine Alert */}
          {analysis.doctrine_alert && (
            <AnalysisSection icon="⚠️" title="Doctrine Alert" color="#a855f7">
              <p style={{ color: 'rgba(255,255,255,0.7)', margin: 0 }}>{analysis.doctrine_alert}</p>
            </AnalysisSection>
          )}

          {/* Insights */}
          {analysis.insights.length > 0 && (
            <AnalysisSection icon="💡" title="Key Insights" color="#ffcc00">
              <ul style={{ margin: 0, paddingLeft: '1.25rem', color: 'rgba(255,255,255,0.7)' }}>
                {analysis.insights.map((insight, idx) => (
                  <li key={idx} style={{ marginBottom: '0.75rem', lineHeight: 1.6 }}>{insight}</li>
                ))}
              </ul>
            </AnalysisSection>
          )}

          {/* Recommendations */}
          {analysis.recommendations.length > 0 && (
            <AnalysisSection icon="📈" title="Trading Recommendations" color="#00ff88">
              <ul style={{ margin: 0, paddingLeft: '1.25rem', color: 'rgba(255,255,255,0.7)' }}>
                {analysis.recommendations.map((rec, idx) => (
                  <li key={idx} style={{ marginBottom: '0.75rem', lineHeight: 1.6 }}>{rec}</li>
                ))}
              </ul>
            </AnalysisSection>
          )}

          {/* Risk Warnings */}
          {analysis.risk_warnings && analysis.risk_warnings.length > 0 && (
            <AnalysisSection icon="⚠️" title="Risk Warnings" color="#ff4444" variant="danger">
              <ul style={{ margin: 0, paddingLeft: '1.25rem', color: 'rgba(255,255,255,0.7)' }}>
                {analysis.risk_warnings.map((warning, idx) => (
                  <li key={idx} style={{ marginBottom: '0.5rem', lineHeight: 1.5 }}>{warning}</li>
                ))}
              </ul>
            </AnalysisSection>
          )}
        </div>
      ) : (
        <div style={{ padding: '2rem', textAlign: 'center', color: 'rgba(255,255,255,0.5)' }}>
          Loading market intelligence...
        </div>
      )}
    </div>
  );
}

interface AnalysisSectionProps {
  icon: string;
  title: string;
  color: string;
  variant?: 'default' | 'danger';
  children: React.ReactNode;
}

function AnalysisSection({ icon, title, color, variant = 'default', children }: AnalysisSectionProps) {
  const isDanger = variant === 'danger';

  return (
    <div style={{
      padding: '1.5rem',
      background: isDanger ? `rgba(255,68,68,0.1)` : 'rgba(0,0,0,0.3)',
      borderRadius: '10px',
      border: `1px solid ${isDanger ? 'rgba(255,68,68,0.3)' : `${color}33`}`,
      borderLeft: `3px solid ${color}`
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
        {icon && <span>{icon}</span>}
        <h3 style={{ color, margin: 0, fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{title}</h3>
      </div>
      {children}
    </div>
  );
}
