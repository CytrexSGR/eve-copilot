import { type ReactNode } from 'react';

interface ModuleGateProps {
  module: string;
  children: ReactNode;
  preview?: boolean;
  seatRequired?: boolean;
  fallback?: ReactNode;
}

export function ModuleGate({ children }: ModuleGateProps) {
  // Feature gating disabled — all modules accessible to all users
  return <>{children}</>;
}
