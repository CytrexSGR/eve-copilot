import { useState } from 'react';
import { Globe, RefreshCw, TrendingUp, Map, Zap } from 'lucide-react';
import { MyColonies, Opportunities, SystemPlanner, PIOptimizerTab } from '../components/pi';

type TabType = 'colonies' | 'opportunities' | 'planner' | 'optimizer';

export default function PlanetaryIndustry() {
  const [activeTab, setActiveTab] = useState<TabType>('colonies');

  return (
    <div className="pi-dashboard">
      <div className="page-header">
        <h1><Globe size={28} /> Planetary Industry</h1>
        <p>Manage colonies, find opportunities, plan systems</p>
      </div>

      <div className="pi-tabs">
        <button
          className={`pi-tab ${activeTab === 'colonies' ? 'active' : ''}`}
          onClick={() => setActiveTab('colonies')}
        >
          <RefreshCw size={16} /> My Colonies
        </button>
        <button
          className={`pi-tab ${activeTab === 'opportunities' ? 'active' : ''}`}
          onClick={() => setActiveTab('opportunities')}
        >
          <TrendingUp size={16} /> Opportunities
        </button>
        <button
          className={`pi-tab ${activeTab === 'planner' ? 'active' : ''}`}
          onClick={() => setActiveTab('planner')}
        >
          <Map size={16} /> System Planner
        </button>
        <button
          className={`pi-tab ${activeTab === 'optimizer' ? 'active' : ''}`}
          onClick={() => setActiveTab('optimizer')}
        >
          <Zap size={16} /> Optimizer
        </button>
      </div>

      <div className="pi-content">
        {activeTab === 'colonies' && <MyColonies />}
        {activeTab === 'opportunities' && <Opportunities />}
        {activeTab === 'planner' && <SystemPlanner />}
        {activeTab === 'optimizer' && <PIOptimizerTab />}
      </div>
    </div>
  );
}
