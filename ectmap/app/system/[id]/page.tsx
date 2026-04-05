'use client';

import { useRouter, useParams } from 'next/navigation';
import SystemDetail from '@/app/components/SystemDetail';

export default function SystemPage() {
  const router = useRouter();
  const params = useParams();
  const systemId = parseInt(params.id as string, 10);

  if (isNaN(systemId)) {
    return (
      <div className="h-screen w-screen bg-black flex items-center justify-center">
        <div className="text-white">Invalid system ID</div>
      </div>
    );
  }

  return (
    <div className="h-screen w-screen">
      <SystemDetail systemId={systemId} onClose={() => router.push('/')} />
    </div>
  );
}
