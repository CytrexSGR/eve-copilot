# EVE Online Interactive Map

An interactive, full-screen map of New Eden for EVE Online.

**Created by [EC Trade](http://edencom.net/)** | [Discord](https://discord.gg/dexSsJYYbv)

## Project Status

This public repository provides an easy plug-and-play version of the EVE Online Interactive Map that runs directly from SDE files. However, **this project is not actively maintained**.

A forked private version is maintained and hosted at [map.edencom.net](http://map.edencom.net). The production version uses a database-backed architecture rather than direct SDE file loading, as our deployment platform (Vercel) doesn't handle large static SDE files efficiently. We wanted to release this simpler filesystem-based version publicly before transitioning to the database approach, so the community could easily self-host and modify the map.

For the most up-to-date and feature-rich experience, visit [map.edencom.net](http://map.edencom.net).

## Features

- Full-screen interactive canvas map with pan and zoom
- View all K-space regions and systems
- Multiple color modes:
  - **Region**: Color by region
  - **Security**: Color by security status (high-sec, low-sec, null-sec)
  - **Faction Warfare**: View faction warfare sovereignty
  - **Alliance**: View alliance sovereignty
- Stargate connections visualization
- System search with autocomplete
- Detailed system view with:
  - Star, planets, moons, asteroid belts
  - Stargates and NPC stations
  - Orbital mechanics visualization

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- EVE Online Static Data Export (SDE) files

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/ectkirk/ectmap.git
cd ectmap
```

2. **Install dependencies**

```bash
npm install
```

3. **Download EVE Online SDE data**

   a. Visit the [EVE Online Developers - Static Data Export](https://developers.eveonline.com/static-data) page

   b. Download the **JSON Lines** format (currently: [eve-online-static-data-3103065-jsonl.zip](https://developers.eveonline.com/static-data/tranquility/eve-online-static-data-3103065-jsonl.zip))

   c. Extract the ZIP file

   d. Copy the following JSONL files from the extracted archive to `public/sde/`:

   **Required files:**
   - `mapRegions.jsonl`
   - `mapConstellations.jsonl`
   - `mapSolarSystems.jsonl`
   - `mapStargates.jsonl`
   - `mapPlanets.jsonl`
   - `mapMoons.jsonl`
   - `mapAsteroidBelts.jsonl`
   - `mapStars.jsonl`
   - `npcStations.jsonl`
   - `npcCorporations.jsonl`
   - `stationOperations.jsonl`
   - `stationServices.jsonl`
   - `types.jsonl`

   Example commands (Linux/Mac):
   ```bash
   # After extracting the SDE zip file
   cp path/to/extracted/sde/mapRegions.jsonl public/sde/
   cp path/to/extracted/sde/mapConstellations.jsonl public/sde/
   cp path/to/extracted/sde/mapSolarSystems.jsonl public/sde/
   cp path/to/extracted/sde/mapStargates.jsonl public/sde/
   cp path/to/extracted/sde/mapPlanets.jsonl public/sde/
   cp path/to/extracted/sde/mapMoons.jsonl public/sde/
   cp path/to/extracted/sde/mapAsteroidBelts.jsonl public/sde/
   cp path/to/extracted/sde/mapStars.jsonl public/sde/
   cp path/to/extracted/sde/npcStations.jsonl public/sde/
   cp path/to/extracted/sde/npcCorporations.jsonl public/sde/
   cp path/to/extracted/sde/stationOperations.jsonl public/sde/
   cp path/to/extracted/sde/stationServices.jsonl public/sde/
   cp path/to/extracted/sde/types.jsonl public/sde/
   ```

   Your `public/sde/` directory should look like this:
   ```
   public/sde/
   ├── mapRegions.jsonl
   ├── mapConstellations.jsonl
   ├── mapSolarSystems.jsonl
   ├── mapStargates.jsonl
   ├── mapPlanets.jsonl
   ├── mapMoons.jsonl
   ├── mapAsteroidBelts.jsonl
   ├── mapStars.jsonl
   ├── npcStations.jsonl
   ├── npcCorporations.jsonl
   ├── stationOperations.jsonl
   ├── stationServices.jsonl
   └── types.jsonl
   ```

4. **Run the development server**

```bash
npm run dev
```

5. **Open [http://localhost:3000](http://localhost:3000)** to view the map

## Production Build

```bash
npm run build
npm start
```

## Data Source

This project uses EVE Online's Static Data Export (SDE) for map data. The SDE is provided by CCP Games and contains comprehensive universe data including:

- Solar system positions and connections
- Celestial objects (stars, planets, moons, asteroid belts)
- NPC stations and corporations
- Station operations and services

The application loads these files from the `public/sde/` directory using efficient JSONL streaming to minimize memory usage.

## Tech Stack

- **Next.js 14** - App Router with React Server Components
- **TypeScript** - Type-safe development
- **Canvas API** - High-performance map rendering
- **Tailwind CSS** - Styling
- **EVE ESI API** - Live sovereignty data (faction warfare and alliance)

## Project Structure

```
ectmap/
├── app/                      # Next.js app directory
│   ├── api/                  # API routes
│   │   ├── map/              # Map data endpoints
│   │   ├── sovereignty/      # Faction warfare data
│   │   └── alliance-sovereignty/  # Alliance sovereignty data
│   ├── components/           # React components
│   │   ├── StarMap.tsx       # Main interactive map
│   │   └── SystemDetail.tsx  # System detail view
│   └── system/[id]/          # Dynamic system pages
├── lib/                      # Shared utilities
│   ├── sde-loader.ts         # SDE data streaming loader
│   ├── sde-types.ts          # TypeScript type definitions
│   ├── esi-agent.ts          # EVE ESI API client
│   └── eve-images.ts         # Image utilities and formatters
├── public/sde/               # SDE data files (you populate this)
└── README.md
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Created by EC Trade** - [http://edencom.net/](http://edencom.net/) | [Discord](https://discord.gg/dexSsJYYbv)

---

This project is not affiliated with or endorsed by CCP Games.

EVE Online and the EVE logo are registered trademarks of CCP hf. All EVE Online materials are the intellectual property of CCP hf.
