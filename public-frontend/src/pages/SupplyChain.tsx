import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { formatISKCompact } from '../utils/format';

const API_BASE = 'http://localhost:8000';

interface Alliance {
  id: number;
  name: string;
  ticker: string;
  has_industry_data: boolean;
  has_cargo_data: boolean;
}

interface IndustrySystem {
  system_id: number;
  system_name: string;
  index: number;
}

interface Midpoint {
  system_id: number;
  system_name: string;
  security: number;
  cyno_deaths: number;
  hauler_deaths: number;
  confidence: number;
}

interface Route {
  midpoint: string;
  destination: string;
  distance_ly: number;
  confidence: number;
  observations: number;
  value_lost: number;
}

interface HaulerStats {
  jf: { losses: number; value: number };
  dst: { losses: number; value: number };
  br: { losses: number; value: number };
  freighter: { losses: number; value: number };
  total_losses: number;
  total_value: number;
}

interface CargoCategory {
  count: number;
  value: number;
  cargo_value: number;
  percentage: number;
}

interface SupplyChainReport {
  alliance: Alliance;
  generated_at: string;
  industry: {
    alliance_id: number;
    industrial_systems: number;
    manufacturing: {
      average: number;
      maximum: number;
      top_systems: IndustrySystem[];
    };
    reaction: {
      average: number;
      maximum: number;
      top_systems: IndustrySystem[];
    };
    trend_7d_percent: number | null;
    assessment: string;
  };
  logistics: {
    midpoints: Midpoint[];
    routes: Route[];
    hauler_stats: HaulerStats;
    assessment: string;
  };
  cargo: {
    total_hauler_losses: number;
    total_value_lost: number;
    category_distribution: Record<string, CargoCategory>;
    top_pilots: Array<{
      character_id: number;
      character_name?: string;
      losses: number;
      primary_role: string;
      total_value_lost: number;
    }>;
    assessment: string;
  };
}

// Use centralized formatISK
const formatISK = formatISKCompact;

function IndexBar({ value, max = 0.15 }: { value: number; max?: number }) {
  const percent = Math.min((value / max) * 100, 100);
  const color = percent > 66 ? '#3fb950' : percent > 33 ? '#d29922' : '#8b949e';

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${percent}%`, backgroundColor: color }}
        />
      </div>
      <span className="text-sm text-gray-400 w-16 text-right">{value.toFixed(4)}</span>
    </div>
  );
}

function AllianceList() {
  const [alliances, setAlliances] = useState<Alliance[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/api/supply-chain/alliances`)
      .then(res => res.json())
      .then(data => {
        setAlliances(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <div className="text-center py-8 text-gray-400">Loading alliances...</div>;
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {alliances.map(alliance => (
        <Link
          key={alliance.id}
          to={`/supply-chain/${alliance.id}`}
          className="bg-[#161b22] border border-[#30363d] rounded-lg p-4 hover:border-[#58a6ff] transition-colors"
        >
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-lg font-semibold text-[#e6edf3]">{alliance.name}</h3>
            <span className="text-[#8b949e] font-mono">[{alliance.ticker}]</span>
          </div>
          <div className="flex gap-2 mt-3">
            {alliance.has_industry_data && (
              <span className="px-2 py-1 text-xs rounded bg-[#238636]/20 text-[#3fb950]">
                Industry Data
              </span>
            )}
            {alliance.has_cargo_data && (
              <span className="px-2 py-1 text-xs rounded bg-[#1f6feb]/20 text-[#58a6ff]">
                Cargo Data
              </span>
            )}
            {!alliance.has_industry_data && !alliance.has_cargo_data && (
              <span className="px-2 py-1 text-xs rounded bg-[#6e7681]/20 text-[#8b949e]">
                No Data
              </span>
            )}
          </div>
        </Link>
      ))}
    </div>
  );
}

function AllianceReport({ allianceId }: { allianceId: number }) {
  const [report, setReport] = useState<SupplyChainReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetch(`${API_BASE}/api/supply-chain/${allianceId}`)
      .then(res => {
        if (!res.ok) throw new Error('Failed to load report');
        return res.json();
      })
      .then(data => {
        setReport(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, [allianceId]);

  if (loading) {
    return <div className="text-center py-8 text-gray-400">Loading supply chain data...</div>;
  }

  if (error || !report) {
    return <div className="text-center py-8 text-red-400">{error || 'Failed to load report'}</div>;
  }

  const { industry, logistics, cargo } = report;
  const sortedCategories = Object.entries(cargo.category_distribution)
    .sort((a, b) => b[1].percentage - a[1].percentage);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-[#e6edf3]">{report.alliance.name}</h2>
          <p className="text-[#8b949e]">[{report.alliance.ticker}] - Supply Chain Intelligence</p>
        </div>
        <Link to="/supply-chain" className="text-[#58a6ff] hover:underline">
          &larr; Back to List
        </Link>
      </div>

      {/* Industry Section */}
      <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-5">
        <h3 className="text-lg font-semibold text-[#e6edf3] mb-4 flex items-center gap-2">
          <span className="text-xl">🏭</span> Industrial Capacity
        </h3>

        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <div className="text-sm text-[#8b949e] mb-1">Industrial Systems</div>
            <div className="text-3xl font-bold text-[#e6edf3]">{industry.industrial_systems}</div>

            {industry.trend_7d_percent !== null && (
              <div className={`text-sm mt-1 ${industry.trend_7d_percent > 0 ? 'text-[#3fb950]' : 'text-[#f85149]'}`}>
                {industry.trend_7d_percent > 0 ? '↑' : '↓'} {Math.abs(industry.trend_7d_percent).toFixed(1)}% (7d)
              </div>
            )}
          </div>

          <div className="space-y-3">
            <div>
              <div className="text-sm text-[#8b949e] mb-1">Manufacturing Index</div>
              <IndexBar value={industry.manufacturing.maximum} />
            </div>
            <div>
              <div className="text-sm text-[#8b949e] mb-1">Reaction Index</div>
              <IndexBar value={industry.reaction.maximum} />
            </div>
          </div>
        </div>

        {industry.manufacturing.top_systems.length > 0 && (
          <div className="mt-4">
            <div className="text-sm text-[#8b949e] mb-2">Top Manufacturing Systems</div>
            <div className="grid gap-2">
              {industry.manufacturing.top_systems.slice(0, 5).map((sys, i) => (
                <div key={sys.system_id} className="flex items-center justify-between bg-[#0d1117] rounded px-3 py-2">
                  <span className="text-[#e6edf3]">
                    <span className="text-[#8b949e] mr-2">#{i + 1}</span>
                    {sys.system_name}
                  </span>
                  <span className="text-[#3fb950] font-mono">{sys.index.toFixed(4)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="mt-4 text-sm text-[#8b949e] italic">{industry.assessment}</div>
      </div>

      {/* Logistics Section */}
      <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-5">
        <h3 className="text-lg font-semibold text-[#e6edf3] mb-4 flex items-center gap-2">
          <span className="text-xl">🚀</span> Logistics Routes
        </h3>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-4">
          <div className="bg-[#0d1117] rounded p-3">
            <div className="text-sm text-[#8b949e]">JF Losses</div>
            <div className="text-xl font-bold text-[#e6edf3]">{logistics.hauler_stats.jf.losses}</div>
            <div className="text-sm text-[#f85149]">{formatISK(logistics.hauler_stats.jf.value)} ISK</div>
          </div>
          <div className="bg-[#0d1117] rounded p-3">
            <div className="text-sm text-[#8b949e]">Freighter</div>
            <div className="text-xl font-bold text-[#e6edf3]">{logistics.hauler_stats.freighter?.losses || 0}</div>
            <div className="text-sm text-[#f85149]">{formatISK(logistics.hauler_stats.freighter?.value || 0)} ISK</div>
          </div>
          <div className="bg-[#0d1117] rounded p-3">
            <div className="text-sm text-[#8b949e]">DST Losses</div>
            <div className="text-xl font-bold text-[#e6edf3]">{logistics.hauler_stats.dst.losses}</div>
            <div className="text-sm text-[#f85149]">{formatISK(logistics.hauler_stats.dst.value)} ISK</div>
          </div>
          <div className="bg-[#0d1117] rounded p-3">
            <div className="text-sm text-[#8b949e]">BR Losses</div>
            <div className="text-xl font-bold text-[#e6edf3]">{logistics.hauler_stats.br.losses}</div>
            <div className="text-sm text-[#f85149]">{formatISK(logistics.hauler_stats.br.value)} ISK</div>
          </div>
          <div className="bg-[#0d1117] rounded p-3">
            <div className="text-sm text-[#8b949e]">Total Value</div>
            <div className="text-xl font-bold text-[#f85149]">{formatISK(logistics.hauler_stats.total_value)} ISK</div>
            <div className="text-sm text-[#8b949e]">{logistics.hauler_stats.total_losses} ships</div>
          </div>
        </div>

        {logistics.midpoints.length > 0 && (
          <div className="mb-4">
            <div className="text-sm text-[#8b949e] mb-2">Identified Midpoints</div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-[#8b949e] border-b border-[#30363d]">
                    <th className="text-left py-2">System</th>
                    <th className="text-right py-2">Security</th>
                    <th className="text-right py-2">Cyno Deaths</th>
                    <th className="text-right py-2">Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {logistics.midpoints.map(mp => (
                    <tr key={mp.system_id} className="border-b border-[#21262d]">
                      <td className="py-2 text-[#e6edf3]">{mp.system_name}</td>
                      <td className="py-2 text-right text-[#d29922]">{mp.security.toFixed(2)}</td>
                      <td className="py-2 text-right text-[#f85149]">{mp.cyno_deaths}</td>
                      <td className="py-2 text-right text-[#3fb950]">{(mp.confidence * 100).toFixed(0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {logistics.routes.length > 0 && (
          <div className="mb-4">
            <div className="text-sm text-[#8b949e] mb-2">Detected Routes</div>
            <div className="space-y-2">
              {logistics.routes.map((route, i) => (
                <div key={i} className="bg-[#0d1117] rounded px-3 py-2 flex items-center justify-between">
                  <span className="text-[#e6edf3]">
                    {route.midpoint} <span className="text-[#8b949e]">→</span> {route.destination}
                  </span>
                  <div className="flex items-center gap-4 text-sm">
                    <span className="text-[#8b949e]">{route.distance_ly.toFixed(1)} LY</span>
                    <span className="text-[#3fb950]">{(route.confidence * 100).toFixed(0)}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="text-sm text-[#8b949e] italic">{logistics.assessment}</div>
      </div>

      {/* Cargo Section */}
      <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-5">
        <h3 className="text-lg font-semibold text-[#e6edf3] mb-4 flex items-center gap-2">
          <span className="text-xl">📦</span> Cargo Analysis
        </h3>

        <div className="grid md:grid-cols-2 gap-4 mb-4">
          <div className="bg-[#0d1117] rounded p-3">
            <div className="text-sm text-[#8b949e]">Total Hauler Losses</div>
            <div className="text-2xl font-bold text-[#e6edf3]">{cargo.total_hauler_losses}</div>
          </div>
          <div className="bg-[#0d1117] rounded p-3">
            <div className="text-sm text-[#8b949e]">Total Value Lost</div>
            <div className="text-2xl font-bold text-[#f85149]">{formatISK(cargo.total_value_lost)} ISK</div>
          </div>
        </div>

        {sortedCategories.length > 0 && (
          <div className="mb-4">
            <div className="text-sm text-[#8b949e] mb-2">Cargo Distribution</div>
            <div className="space-y-2">
              {sortedCategories.map(([category, data]) => (
                <div key={category} className="bg-[#0d1117] rounded px-3 py-2">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[#e6edf3] font-medium">{category.replace(/_/g, ' ')}</span>
                    <span className="text-[#8b949e]">{data.count} ({data.percentage.toFixed(0)}%)</span>
                  </div>
                  <div className="h-2 bg-[#21262d] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#58a6ff] rounded-full"
                      style={{ width: `${data.percentage}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {cargo.top_pilots.length > 0 && (
          <div className="mb-4">
            <div className="text-sm text-[#8b949e] mb-2">Key Logistics Personnel</div>
            <div className="space-y-2">
              {cargo.top_pilots.map(pilot => (
                <div key={pilot.character_id} className="bg-[#0d1117] rounded px-3 py-2 flex items-center justify-between">
                  <span className="text-[#e6edf3]">{pilot.character_name || `Pilot ${pilot.character_id}`}</span>
                  <div className="flex items-center gap-4 text-sm">
                    <span className="text-[#8b949e]">{pilot.losses} losses</span>
                    <span className="text-[#bc8cff]">{pilot.primary_role.replace(/_/g, ' ')}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="text-sm text-[#8b949e] italic">{cargo.assessment}</div>
      </div>
    </div>
  );
}

export default function SupplyChain() {
  const { allianceId } = useParams<{ allianceId: string }>();

  return (
    <div className="min-h-screen bg-[#0d1117] text-[#e6edf3]">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-2">Supply Chain Intelligence</h1>
        <p className="text-[#8b949e] mb-8">
          Industrial capacity, logistics routes, and cargo analysis
        </p>

        {allianceId ? (
          <AllianceReport allianceId={parseInt(allianceId)} />
        ) : (
          <AllianceList />
        )}
      </div>
    </div>
  );
}
