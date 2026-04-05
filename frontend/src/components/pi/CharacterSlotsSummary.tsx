import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { User, RefreshCw } from 'lucide-react';
import { getCharacters, getCharacterSlots, syncCharacterSkills } from '../../api/pi';
import type { PICharacter, PICharacterSlots } from '../../api/pi';

interface CharacterSlotsSummaryProps {
  onSlotsLoaded?: (slots: PICharacterSlots[]) => void;
}

export function CharacterSlotsSummary({ onSlotsLoaded }: CharacterSlotsSummaryProps) {
  const queryClient = useQueryClient();
  const [syncingAll, setSyncingAll] = useState(false);

  // Fetch characters
  const { data: characters, isLoading: loadingChars } = useQuery({
    queryKey: ['pi-characters'],
    queryFn: getCharacters,
  });

  // Fetch slots for all characters once we have them
  const characterIds = characters?.map((c: PICharacter) => c.character_id) || [];
  const { data: slots, isLoading: loadingSlots, refetch: refetchSlots } = useQuery({
    queryKey: ['pi-character-slots', characterIds],
    queryFn: () => getCharacterSlots(characterIds),
    enabled: characterIds.length > 0,
  });

  // Call onSlotsLoaded callback when slots change
  useEffect(() => {
    if (slots && onSlotsLoaded) {
      onSlotsLoaded(slots);
    }
  }, [slots, onSlotsLoaded]);

  // Sync skills mutation
  const syncMutation = useMutation({
    mutationFn: syncCharacterSkills,
    onSuccess: () => {
      // Refetch slots after successful sync
      refetchSlots();
    },
  });

  const handleSyncAll = async () => {
    if (!characters || syncingAll) return;

    setSyncingAll(true);
    try {
      // Sync skills for each character sequentially
      for (const char of characters) {
        await syncMutation.mutateAsync(char.character_id);
      }
      // Invalidate and refetch slots
      queryClient.invalidateQueries({ queryKey: ['pi-character-slots'] });
    } finally {
      setSyncingAll(false);
    }
  };

  // Calculate totals
  const totals = slots?.reduce(
    (acc, slot) => ({
      used: acc.used + slot.used_planets,
      max: acc.max + slot.max_planets,
      free: acc.free + slot.free_planets,
    }),
    { used: 0, max: 0, free: 0 }
  ) || { used: 0, max: 0, free: 0 };

  const isLoading = loadingChars || loadingSlots;

  if (isLoading) {
    return (
      <div className="character-slots-summary">
        <div className="loading-inline">Loading character slots...</div>
      </div>
    );
  }

  if (!characters || characters.length === 0) {
    return (
      <div className="character-slots-summary">
        <div className="empty-state">
          <User size={32} />
          <p>No characters found</p>
        </div>
      </div>
    );
  }

  return (
    <div className="character-slots-summary">
      <div className="slots-header">
        <h3>Character PI Slots</h3>
        <button
          className="btn btn-secondary btn-sm"
          onClick={handleSyncAll}
          disabled={syncingAll}
        >
          <RefreshCw size={14} className={syncingAll ? 'spin' : ''} />
          Sync Skills
        </button>
      </div>

      <div className="character-slots-grid">
        {slots?.map((slot) => (
          <CharacterSlotCard key={slot.character_id} slot={slot} />
        ))}
      </div>

      <div className="slots-total">
        <div className="total-label">Total Slots</div>
        <div className="total-values">
          <span className="used">{totals.used}</span>
          <span className="separator">/</span>
          <span className="max">{totals.max}</span>
          <span className="free">({totals.free} free)</span>
        </div>
        <div className="total-progress">
          <div
            className="total-progress-fill"
            style={{
              width: totals.max > 0 ? `${(totals.used / totals.max) * 100}%` : '0%',
            }}
          />
        </div>
      </div>
    </div>
  );
}

interface CharacterSlotCardProps {
  slot: PICharacterSlots;
}

function CharacterSlotCard({ slot }: CharacterSlotCardProps) {
  const usagePercent = slot.max_planets > 0
    ? (slot.used_planets / slot.max_planets) * 100
    : 0;

  const getUsageClass = () => {
    if (usagePercent >= 100) return 'usage-full';
    if (usagePercent >= 80) return 'usage-high';
    if (usagePercent >= 50) return 'usage-medium';
    return 'usage-low';
  };

  return (
    <div className="character-slot-card">
      <div className="slot-card-header">
        <img
          src={`https://images.evetech.net/characters/${slot.character_id}/portrait?size=32`}
          alt={slot.character_name}
          className="character-portrait"
        />
        <div className="slot-card-info">
          <span className="character-name">{slot.character_name}</span>
          <span className="slot-usage">
            {slot.used_planets}/{slot.max_planets} planets
          </span>
        </div>
      </div>
      <div className={`slot-progress ${getUsageClass()}`}>
        <div
          className="slot-progress-fill"
          style={{ width: `${usagePercent}%` }}
        />
      </div>
    </div>
  );
}
