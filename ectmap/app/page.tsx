import StarMap from './components/StarMap';

interface PageProps {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}

export default async function MapPage({ searchParams }: PageProps) {
  const params = await searchParams;

  // Parse status level filters (e.g., "gank,brawl,battle,hellcamp")
  const levelsParam = params.levels as string;
  const enabledLevels = levelsParam ? levelsParam.split(',') : undefined;

  return (
    <div className="h-screen w-screen">
      <StarMap
        initialColorMode={params.colorMode as string}
        initialShowCampaigns={params.showCampaigns !== 'false'}
        initialKillsMinutes={params.killsMinutes ? parseInt(params.killsMinutes as string) : undefined}
        initialActivityMinutes={params.minutes ? parseInt(params.minutes as string) : undefined}
        initialRegion={params.region as string}
        snapshotMode={params.snapshot === 'true'}
        externalFilters={enabledLevels ? true : false}
        enabledStatusLevels={enabledLevels}
        entityType={params.entityType as string}
        entityId={params.entityId as string}
        entityDays={params.days ? parseInt(params.days as string) : undefined}
      />
    </div>
  );
}
