import type { Meta, StoryObj } from '@storybook/react';
import { LiveActivitySection } from './LiveActivitySection';

const meta: Meta<typeof LiveActivitySection> = {
  title: 'WarfareIntel/LiveActivitySection',
  component: LiveActivitySection,
  parameters: { layout: 'padded' },
};
export default meta;
type Story = StoryObj<typeof LiveActivitySection>;

export const Default: Story = {
  args: {
    battles: [
      {
        battle_id: 102977,
        system_id: 30004759,
        system_name: 'M-OEE8',
        region_name: 'Tribute',
        security: -0.4,
        total_kills: 87,
        total_isk_destroyed: 45_000_000_000,
        last_milestone: 80,
        started_at: new Date(Date.now() - 3600000).toISOString(),
        last_kill_at: new Date(Date.now() - 120000).toISOString(),
        duration_minutes: 3,
        telegram_sent: true,
        intensity: 'extreme',
        status_level: 'battle',
        top_ships: [{ ship_name: 'Muninn', count: 12 }, { ship_name: 'Eagle', count: 8 }],
      },
      {
        battle_id: 102980,
        system_id: 30002813,
        system_name: 'HED-GP',
        region_name: 'Catch',
        security: -0.3,
        total_kills: 25,
        total_isk_destroyed: 5_000_000_000,
        last_milestone: 20,
        started_at: new Date(Date.now() - 7200000).toISOString(),
        last_kill_at: new Date(Date.now() - 600000).toISOString(),
        duration_minutes: 15,
        telegram_sent: false,
        intensity: 'moderate',
        status_level: 'brawl',
      },
    ],
    recentKills: [
      { killmail_id: 1001, ship_name: 'Naglfar', value: 8_500_000_000 },
      { killmail_id: 1002, ship_name: 'Muninn', value: 350_000_000 },
      { killmail_id: 1003, ship_name: 'Vexor Navy Issue', value: 120_000_000 },
    ],
    loading: false,
  },
};

export const Loading: Story = {
  args: {
    battles: [],
    recentKills: [],
    loading: true,
  },
};

export const NoBattles: Story = {
  args: {
    battles: [],
    recentKills: [
      { killmail_id: 1001, ship_name: 'Caracal', value: 45_000_000 },
    ],
    loading: false,
  },
};
