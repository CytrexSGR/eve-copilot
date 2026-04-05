import type { Meta, StoryObj } from '@storybook/react';
import { EnrichedModuleList } from './EnrichedModuleList';
import { mockDrakeStats } from '../../../.storybook/mocks/data/fittings';

const meta: Meta<typeof EnrichedModuleList> = {
  title: 'Fittings & Navigation/Fittings/EnrichedModuleList',
  component: EnrichedModuleList,
  tags: ['autodocs'],
};
export default meta;
type Story = StoryObj<typeof EnrichedModuleList>;

const statsWithModuleDetails = {
  ...mockDrakeStats,
  module_details: [
    { type_id: 3170, type_name: 'Heavy Missile Launcher II', slot_type: 'high', flag: 27, quantity: 1, cpu: 48, pg: 60, cap_need: 0, cycle_time_ms: 4320, cap_per_sec: 0, hardpoint_type: 'launcher' },
    { type_id: 3170, type_name: 'Heavy Missile Launcher II', slot_type: 'high', flag: 28, quantity: 1, cpu: 48, pg: 60, cap_need: 0, cycle_time_ms: 4320, cap_per_sec: 0, hardpoint_type: 'launcher' },
    { type_id: 3170, type_name: 'Heavy Missile Launcher II', slot_type: 'high', flag: 29, quantity: 1, cpu: 48, pg: 60, cap_need: 0, cycle_time_ms: 4320, cap_per_sec: 0, hardpoint_type: 'launcher' },
    { type_id: 3841, type_name: 'Large Shield Extender II', slot_type: 'mid', flag: 19, quantity: 1, cpu: 50, pg: 1, cap_need: 0, cycle_time_ms: 0, cap_per_sec: 0 },
    { type_id: 2281, type_name: 'Multispectrum Shield Hardener II', slot_type: 'mid', flag: 21, quantity: 1, cpu: 35, pg: 1, cap_need: 32, cycle_time_ms: 10000, cap_per_sec: 3.2 },
    { type_id: 22291, type_name: 'Ballistic Control System II', slot_type: 'low', flag: 11, quantity: 1, cpu: 30, pg: 1, cap_need: 0, cycle_time_ms: 0, cap_per_sec: 0 },
    { type_id: 2048, type_name: 'Damage Control II', slot_type: 'low', flag: 14, quantity: 1, cpu: 25, pg: 1, cap_need: 0, cycle_time_ms: 0, cap_per_sec: 0 },
    { type_id: 31752, type_name: 'Medium Core Defense Field Extender I', slot_type: 'rig', flag: 92, quantity: 1, cpu: 0, pg: 0, cap_need: 0, cycle_time_ms: 0, cap_per_sec: 0 },
  ],
};

export const Default: Story = {
  args: {
    stats: statsWithModuleDetails,
  },
};

export const NoModuleDetails: Story = {
  args: {
    stats: { ...mockDrakeStats, module_details: undefined },
  },
};
