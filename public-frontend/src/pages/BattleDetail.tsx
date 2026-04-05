import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { battleApi, warApi } from '../services/api';
import type {
  BattleSidesResponse,
  CommanderIntelResponse,
  DamageAnalysisResponse,
  VictimTankAnalysisResponse,
  StrategicContextResponse,
  AttackerLoadoutsResponse,
} from '../services/api';
import { BattleTimeline } from '../components/BattleTimeline';
import { BattleReshipments } from '../components/BattleReshipments';
import {
  BattleHeader,
  BattleSidesPanel,
  BattleKillFeed,
  BattleCommanderIntel,
  BattleShipClasses,
  BattleDoctrines,
  BattleDamageAnalysis,
  BattleContext,
  BattleSovContext,
  BattleVictimTank,
  BattleAttackerLoadouts,
} from '../components/battle';
import { ModuleGate } from '../components/ModuleGate';

interface ActiveBattle {
  battle_id: number;
  system_id: number;
  system_name: string;
  region_name: string;
  security: number;
  total_kills: number;
  total_isk_destroyed: number;
  last_milestone: number;
  started_at: string;
  last_kill_at: string;
  duration_minutes: number;
  telegram_sent: boolean;
  intensity: 'extreme' | 'high' | 'moderate' | 'low';
}

interface Killmail {
  killmail_id: number;
  killmail_time: string;
  solar_system_id: number;
  ship_type_id: number;
  ship_name?: string;
  ship_value: number;
  victim_character_id: number;
  victim_corporation_id: number;
  victim_alliance_id: number | null;
  attacker_count: number;
  is_solo: boolean;
  is_npc: boolean;
}

interface SystemDanger {
  system_id: number;
  danger_score: number;
  kills_24h: number;
  is_dangerous: boolean;
}

interface ShipClassData {
  battle_id?: number;
  system_id?: number;
  hours?: number;
  total_kills: number;
  group_by: string;
  breakdown: {
    [key: string]: number;
  };
}

interface ParticipantAlliance {
  alliance_id: number;
  alliance_name: string;
  kills?: number;
  losses?: number;
  isk_lost?: number;
  corps_involved: number;
}

interface BattleParticipants {
  battle_id: number;
  attackers: {
    alliances: ParticipantAlliance[];
    total_alliances: number;
    total_kills: number;
  };
  defenders: {
    alliances: ParticipantAlliance[];
    total_alliances: number;
    total_losses: number;
    total_isk_lost: number;
  };
}

export function BattleDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [battle, setBattle] = useState<ActiveBattle | null>(null);
  const [recentKills, setRecentKills] = useState<Killmail[]>([]);
  const [systemDanger, setSystemDanger] = useState<SystemDanger | null>(null);
  const [shipClasses, setShipClasses] = useState<ShipClassData | null>(null);
  const [participants, setParticipants] = useState<BattleParticipants | null>(null);
  const [battleSides, setBattleSides] = useState<BattleSidesResponse | null>(null);
  const [commanderIntel, setCommanderIntel] = useState<CommanderIntelResponse | null>(null);
  const [damageAnalysis, setDamageAnalysis] = useState<DamageAnalysisResponse | null>(null);
  const [victimTank, setVictimTank] = useState<VictimTankAnalysisResponse | null>(null);
  const [attackerLoadouts, setAttackerLoadouts] = useState<AttackerLoadoutsResponse | null>(null);
  const [strategicContext, setStrategicContext] = useState<StrategicContextResponse | null>(null);
  const [warSummary, setWarSummary] = useState<{ period_hours: number; total_kills: number; total_isk_destroyed: number; active_systems: number; capital_kills: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isInitialLoad = true;

    const fetchBattle = async () => {
      try {
        // Only show loading skeleton on initial load, not on refresh
        if (isInitialLoad) {
          setLoading(true);
        }
        setError(null);

        // Fetch battle directly by ID (works for both active and ended battles)
        const foundBattle = await battleApi.getBattle(parseInt(id || '0'));

        if (foundBattle) {
          setBattle(foundBattle);

          try {
            const [killsData, dangerData, shipClassData, participantsData, sidesData, intelData, damageData, tankData, ctxData, summaryData, loadoutsData] = await Promise.all([
              battleApi.getBattleKills(foundBattle.battle_id, 500),
              battleApi.getSystemDanger(foundBattle.system_id),
              battleApi.getBattleShipClasses(foundBattle.battle_id, 'category'),
              battleApi.getBattleParticipants(foundBattle.battle_id),
              battleApi.getBattleSides(foundBattle.battle_id),
              battleApi.getCommanderIntel(foundBattle.battle_id),
              battleApi.getDamageAnalysis(foundBattle.battle_id).catch(() => null),
              battleApi.getVictimTankAnalysis(foundBattle.battle_id).catch(() => null),
              battleApi.getStrategicContext(foundBattle.battle_id).catch(() => null),
              warApi.getWarSummary(24).catch(() => null),
              battleApi.getAttackerLoadouts(foundBattle.battle_id).catch(() => null),
            ]);
            setRecentKills(killsData.kills || []);
            setSystemDanger(dangerData);
            setShipClasses(shipClassData);
            setParticipants(participantsData);
            setBattleSides(sidesData);
            setCommanderIntel(intelData);
            setDamageAnalysis(damageData);
            setVictimTank(tankData);
            setStrategicContext(ctxData);
            setWarSummary(summaryData);
            setAttackerLoadouts(loadoutsData);
          } catch (err) {
            console.error('Failed to fetch additional battle data:', err);
          }
        } else {
          setError('Battle not found or no longer active');
        }

        setLoading(false);
        isInitialLoad = false;
      } catch (err: unknown) {
        console.error('Failed to fetch battle:', err);
        // Check if it's a 404 error
        if (err && typeof err === 'object' && 'response' in err) {
          const axiosErr = err as { response?: { status?: number } };
          if (axiosErr.response?.status === 404) {
            setError('Battle not found');
          } else {
            setError('Failed to load battle details');
          }
        } else {
          setError('Failed to load battle details');
        }
        setLoading(false);
        isInitialLoad = false;
      }
    };

    fetchBattle();
    // Auto-refresh every 30 seconds (silent refresh, no loading skeleton)
    const interval = setInterval(fetchBattle, 30000);
    return () => clearInterval(interval);
  }, [id]);

  if (loading) {
    return <div className="skeleton" style={{ height: '500px' }} />;
  }

  if (error || !battle) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
        <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>Warning</div>
        <h2 style={{ marginBottom: '1rem' }}>Battle Not Found</h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>
          {error || 'This battle is no longer active or does not exist.'}
        </p>
        <button
          onClick={() => navigate(-1)}
          style={{
            padding: '0.75rem 1.5rem',
            background: 'var(--accent-blue)',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            fontSize: '1rem',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          &larr; Back
        </button>
      </div>
    );
  }

  return (
    <div>
      {/* Header with Back Button and Battle Info */}
      <BattleHeader
        battle={battle}
        systemDanger={systemDanger}
        capitalShipsLost={commanderIntel?.capitals.lost || []}
        onBack={() => navigate(-1)}
      />

      {/* Battle Sides Panel (FREE) */}
      <BattleSidesPanel
        battleSides={battleSides}
        participants={participants}
        commanderIntel={commanderIntel}
      />

      {/* All detailed analysis panels (GATED) */}
      <ModuleGate module="battle_analysis">
        {/* Sovereignty Campaign Alerts */}
        <BattleSovContext context={strategicContext} />

        {/* Battle Significance Context */}
        <BattleContext
          battleKills={battle.total_kills}
          battleISK={battle.total_isk_destroyed}
          battleCapitalKills={commanderIntel?.capitals.lost?.length || 0}
          warSummary={warSummary}
        />

        {/* Commander Intel Section (includes Combat Analysis) */}
        {commanderIntel && (
          <BattleCommanderIntel
            commanderIntel={commanderIntel}
            recentKills={recentKills}
            systemDanger={systemDanger}
          />
        )}

        {/* Fleet Doctrines - Full Width */}
        {commanderIntel && Object.keys(commanderIntel.doctrines).length > 0 && (
          <BattleDoctrines doctrines={commanderIntel.doctrines} />
        )}

        {/* Attacker Loadout Analysis */}
        <BattleAttackerLoadouts data={attackerLoadouts} />

        {/* Damage Analysis */}
        <BattleDamageAnalysis damageAnalysis={damageAnalysis} />

        {/* Victim Tank Analysis (Dogma Engine) */}
        <BattleVictimTank data={victimTank} />

        {/* Ship Classes */}
        <BattleShipClasses shipClasses={shipClasses} />

        {/* Battle Timeline Visualization */}
        <BattleTimeline
          battleId={battle.battle_id}
          onError={(err) => console.error('Timeline error:', err)}
        />

        {/* Combat Persistence */}
        <BattleReshipments battleId={battle.battle_id} />

        {/* Killmails Table */}
        <BattleKillFeed kills={recentKills} totalKills={battle.total_kills} />
      </ModuleGate>
    </div>
  );
}
