import CapitalMap from './components/CapitalMap'

interface PageProps {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}

export default async function MapPage({ searchParams }: PageProps) {
  const params = await searchParams;

  return (
    <div className="h-screen w-screen">
      <CapitalMap
        initialShowJammers={params.showJammers !== 'false'}
        initialShowTimers={params.showTimers !== 'false'}
        initialRegion={params.region as string}
        snapshotMode={params.snapshot === 'true'}
      />
    </div>
  )
}
