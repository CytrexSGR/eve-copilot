import React, { useMemo } from 'react';
import type { EntityViewProps } from './types';
import { getEctmapBaseUrl } from '../../utils/format';

export const LiveMapView: React.FC<EntityViewProps> = ({ entityType, entityId, days }) => {
  const mapUrl = useMemo(() => {
    return `${getEctmapBaseUrl()}?colorMode=entity_activity&entityType=${entityType}&entityId=${entityId}&days=${days}&showKills=true&showBattles=true&showCampaigns=false`;
  }, [entityType, entityId, days]);

  return (
    <iframe
      src={mapUrl}
      style={{
        width: '100%',
        height: 'calc(100vh - 220px)',
        border: 'none',
        borderRadius: '8px',
      }}
      title="Entity Live Map"
    />
  );
};
