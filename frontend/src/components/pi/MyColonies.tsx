import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { RefreshCw, AlertCircle } from 'lucide-react';
import { getCharacters, getColonies, syncColonies } from '../../api/pi';
import type { PICharacter, PIColony } from '../../api/pi';
import { ColonyCard } from './ColonyCard';
import { ColonyDetailModal } from './ColonyDetailModal';

interface SelectedColony {
  colony: PIColony;
  characterId: number;
}

export function MyColonies() {
  const queryClient = useQueryClient();
  const [syncingCharacter, setSyncingCharacter] = useState<number | null>(null);
  const [selectedColony, setSelectedColony] = useState<SelectedColony | null>(null);

  const { data: characters, isLoading: loadingChars } = useQuery({
    queryKey: ['pi-characters'],
    queryFn: getCharacters,
  });

  const syncMutation = useMutation({
    mutationFn: syncColonies,
    onSuccess: (_, characterId) => {
      queryClient.invalidateQueries({ queryKey: ['pi-colonies', characterId] });
      setSyncingCharacter(null);
    },
    onError: () => {
      setSyncingCharacter(null);
    },
  });

  const handleSyncAll = async () => {
    if (!characters) return;
    for (const char of characters) {
      setSyncingCharacter(char.character_id);
      await syncMutation.mutateAsync(char.character_id);
    }
  };

  const handleSyncOne = (characterId: number) => {
    setSyncingCharacter(characterId);
    syncMutation.mutate(characterId);
  };

  const handleViewDetails = (colony: PIColony, characterId: number) => {
    setSelectedColony({ colony, characterId });
  };

  if (loadingChars) {
    return <div className="loading">Loading characters...</div>;
  }

  if (!characters || characters.length === 0) {
    return (
      <div className="empty-state">
        <AlertCircle size={48} />
        <h3>No Characters Found</h3>
        <p>Authenticate characters at /api/auth/login</p>
      </div>
    );
  }

  return (
    <div className="my-colonies">
      <div className="colonies-header">
        <button
          className="btn btn-primary"
          onClick={handleSyncAll}
          disabled={syncingCharacter !== null}
        >
          <RefreshCw size={16} className={syncingCharacter !== null ? 'spin' : ''} />
          Sync All Characters
        </button>
      </div>

      {characters.map((char) => (
        <CharacterSection
          key={char.character_id}
          character={char}
          isSyncing={syncingCharacter === char.character_id}
          onSync={() => handleSyncOne(char.character_id)}
          onViewDetails={(colony) => handleViewDetails(colony, char.character_id)}
        />
      ))}

      {selectedColony && (
        <ColonyDetailModal
          colony={selectedColony.colony}
          characterId={selectedColony.characterId}
          onClose={() => setSelectedColony(null)}
        />
      )}
    </div>
  );
}

interface CharacterSectionProps {
  character: PICharacter;
  isSyncing: boolean;
  onSync: () => void;
  onViewDetails: (colony: PIColony) => void;
}

function CharacterSection({ character, isSyncing, onSync, onViewDetails }: CharacterSectionProps) {
  const { data: colonies, isLoading } = useQuery({
    queryKey: ['pi-colonies', character.character_id],
    queryFn: () => getColonies(character.character_id),
  });

  return (
    <div className="character-section">
      <div className="character-header">
        <div className="character-info">
          <img
            src={`https://images.evetech.net/characters/${character.character_id}/portrait?size=32`}
            alt={character.character_name}
            className="character-portrait"
          />
          <h3>{character.character_name}</h3>
          <span className="colony-count">
            {colonies?.length || 0} colonies
          </span>
        </div>
        <button
          className="btn btn-secondary btn-sm"
          onClick={onSync}
          disabled={isSyncing}
        >
          <RefreshCw size={14} className={isSyncing ? 'spin' : ''} />
          Sync
        </button>
      </div>

      {isLoading ? (
        <div className="loading-inline">Loading colonies...</div>
      ) : colonies && colonies.length > 0 ? (
        <div className="colonies-grid">
          {colonies.map((colony) => (
            <ColonyCard
              key={colony.planet_id}
              colony={colony}
              onViewDetails={() => onViewDetails(colony)}
            />
          ))}
        </div>
      ) : (
        <div className="no-colonies">
          No colonies found. Click Sync to fetch from ESI.
        </div>
      )}
    </div>
  );
}
