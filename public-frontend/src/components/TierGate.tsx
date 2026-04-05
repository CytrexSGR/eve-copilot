import { type ReactNode } from 'react';

interface TierGateProps {
  requiredTier: string;
  children: ReactNode;
  showPreview?: boolean;
}

export function TierGate({ children }: TierGateProps) {
  // Feature gating disabled — all tiers accessible to all users
  return <>{children}</>;
}
