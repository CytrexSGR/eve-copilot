import SovMap from './components/SovMap';

interface PageProps {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}

export default async function SovMapPage({ searchParams }: PageProps) {
  const params = await searchParams;

  return (
    <div className="h-screen w-screen">
      <SovMap
        initialColorMode={params.colorMode as 'adm' | 'alliance' | 'region'}
        initialShowJammers={params.showJammers !== 'false'}
        initialRegion={params.region as string}
        snapshotMode={params.snapshot === 'true'}
      />
    </div>
  );
}
