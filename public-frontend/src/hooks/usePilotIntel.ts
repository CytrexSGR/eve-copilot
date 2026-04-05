import { useContext } from 'react';
import { PilotIntelContext } from '../context/PilotIntelContext';

export function usePilotIntel() {
  return useContext(PilotIntelContext);
}
