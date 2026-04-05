import { useQuery } from '@tanstack/react-query';
import { X, Clock, AlertTriangle, Factory, Truck, Package } from 'lucide-react';
import { getColonyDetail } from '../../api/pi';
import type { PIColony, PIPin } from '../../api/pi';

interface ColonyDetailModalProps {
  colony: PIColony;
  characterId: number;
  onClose: () => void;
}

const PLANET_COLORS: Record<string, string> = {
  'barren': '#6b7280',
  'gas': '#22c55e',
  'ice': '#06b6d4',
  'lava': '#f97316',
  'oceanic': '#3b82f6',
  'plasma': '#a855f7',
  'storm': '#eab308',
  'temperate': '#10b981',
};

function formatTimeRemaining(expiryTime: string): { text: string; urgent: boolean } {
  const now = new Date();
  const expiry = new Date(expiryTime);
  const diffMs = expiry.getTime() - now.getTime();

  if (diffMs <= 0) {
    return { text: 'Expired', urgent: true };
  }

  const hours = Math.floor(diffMs / (1000 * 60 * 60));
  const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

  if (hours < 1) {
    return { text: `${minutes}m remaining`, urgent: true };
  } else if (hours < 24) {
    return { text: `${hours}h ${minutes}m remaining`, urgent: hours < 6 };
  } else {
    const days = Math.floor(hours / 24);
    const remainingHours = hours % 24;
    return { text: `${days}d ${remainingHours}h remaining`, urgent: false };
  }
}

function categorizePin(pin: PIPin): 'extractor' | 'factory' | 'storage' | 'command' {
  const name = pin.type_name.toLowerCase();
  if (name.includes('extractor')) return 'extractor';
  if (name.includes('industry') || name.includes('processor')) return 'factory';
  if (name.includes('storage') || name.includes('launchpad')) return 'storage';
  return 'command';
}

export function ColonyDetailModal({ colony, characterId, onClose }: ColonyDetailModalProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['pi-colony-detail', characterId, colony.planet_id],
    queryFn: () => getColonyDetail(characterId, colony.planet_id),
  });

  const planetColor = PLANET_COLORS[colony.planet_type.toLowerCase()] || '#6b7280';

  const extractors = data?.pins.filter(p => categorizePin(p) === 'extractor') || [];
  const factories = data?.pins.filter(p => categorizePin(p) === 'factory') || [];
  const storage = data?.pins.filter(p => categorizePin(p) === 'storage') || [];

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content colony-detail-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div className="colony-modal-title">
            <div
              className="planet-icon large"
              style={{ backgroundColor: planetColor }}
            >
              {colony.planet_type.charAt(0).toUpperCase()}
            </div>
            <div>
              <h2>{colony.solar_system_name} - {colony.planet_type}</h2>
              <span className="colony-subtitle">
                Level {colony.upgrade_level} Command Center
              </span>
            </div>
          </div>
          <button className="modal-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          {isLoading ? (
            <div className="loading">Loading colony details...</div>
          ) : error ? (
            <div className="error">Failed to load colony details</div>
          ) : data ? (
            <>
              {/* Extractors Section */}
              <section className="colony-section">
                <h3><Clock size={18} /> Extractors ({extractors.length})</h3>
                {extractors.length === 0 ? (
                  <p className="empty-text">No extractors</p>
                ) : (
                  <div className="pin-list">
                    {extractors.map(pin => {
                      const expiry = pin.expiry_time ? formatTimeRemaining(pin.expiry_time) : null;
                      return (
                        <div key={pin.pin_id} className={`pin-card extractor ${expiry?.urgent ? 'urgent' : ''}`}>
                          <div className="pin-header">
                            <span className="pin-product">{pin.product_name || 'Unknown'}</span>
                            {expiry && (
                              <span className={`pin-expiry ${expiry.urgent ? 'urgent' : ''}`}>
                                {expiry.urgent && <AlertTriangle size={14} />}
                                {expiry.text}
                              </span>
                            )}
                          </div>
                          {pin.qty_per_cycle && pin.cycle_time && (
                            <div className="pin-stats">
                              <span>{pin.qty_per_cycle.toLocaleString()} / {pin.cycle_time / 60}min</span>
                              <span className="hourly-rate">
                                {Math.round(pin.qty_per_cycle * (3600 / pin.cycle_time)).toLocaleString()}/h
                              </span>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </section>

              {/* Factories Section */}
              <section className="colony-section">
                <h3><Factory size={18} /> Factories ({factories.length})</h3>
                {factories.length === 0 ? (
                  <p className="empty-text">No factories</p>
                ) : (
                  <div className="pin-list factories">
                    {factories.map(pin => (
                      <div key={pin.pin_id} className="pin-card factory">
                        <span className="pin-type">{pin.type_name.replace(/.*?(Basic|Advanced|High-Tech)/, '$1')}</span>
                        <span className="pin-schematic">{pin.schematic_name || 'No schematic'}</span>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              {/* Storage Section */}
              <section className="colony-section">
                <h3><Package size={18} /> Storage & Launchpads ({storage.length})</h3>
                {storage.length === 0 ? (
                  <p className="empty-text">No storage facilities</p>
                ) : (
                  <div className="pin-list">
                    {storage.map(pin => (
                      <div key={pin.pin_id} className="pin-card storage">
                        <span className="pin-type">{pin.type_name}</span>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              {/* Routes Section */}
              <section className="colony-section">
                <h3><Truck size={18} /> Routes ({data.routes.length})</h3>
                {data.routes.length === 0 ? (
                  <p className="empty-text">No routes configured</p>
                ) : (
                  <div className="routes-summary">
                    {Object.entries(
                      data.routes.reduce((acc, route) => {
                        acc[route.content_name] = (acc[route.content_name] || 0) + route.quantity;
                        return acc;
                      }, {} as Record<string, number>)
                    ).map(([name, qty]) => (
                      <div key={name} className="route-item">
                        <span className="route-name">{name}</span>
                        <span className="route-qty">{qty.toLocaleString()}/cycle</span>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
