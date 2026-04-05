import NewsTicker from '../NewsTicker';
import { MAX_TICKER_ALERTS, TICKER_REFRESH_MS } from '../../constants';

interface NewsFeedSectionProps {
  maxAlerts?: number;
  refreshInterval?: number;
}

export function NewsFeedSection({
  maxAlerts = MAX_TICKER_ALERTS,
  refreshInterval = TICKER_REFRESH_MS,
}: NewsFeedSectionProps) {
  return (
    <div style={{ marginBottom: '1rem' }}>
      <NewsTicker maxAlerts={maxAlerts} refreshInterval={refreshInterval} />
    </div>
  );
}
