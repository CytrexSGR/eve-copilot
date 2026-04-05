import type { Meta, StoryObj } from '@storybook/react';
import { WarRoomAlertBar } from './WarRoomAlertBar';
import type { WarRoomAlert } from '../hooks/useWarRoomAlerts';

const meta: Meta<typeof WarRoomAlertBar> = {
  title: 'Shared UI/WarRoomAlertBar',
  component: WarRoomAlertBar,
  tags: ['autodocs'],
  parameters: {
    layout: 'fullscreen',
  },
  argTypes: {
    maxVisible: { control: { type: 'range', min: 1, max: 10, step: 1 } },
    rotateInterval: { control: { type: 'range', min: 2000, max: 20000, step: 1000 } },
  },
};

export default meta;
type Story = StoryObj<typeof WarRoomAlertBar>;

const now = new Date();

const sampleAlerts: WarRoomAlert[] = [
  {
    id: '1',
    type: 'battle',
    priority: 'critical',
    icon: '🔥',
    message: 'Capital engagement in KBP7-G',
    detail: '47 capitals on field, Fraternity vs. Pandemic Horde',
    timestamp: now,
    link: '/battle/102977',
  },
  {
    id: '2',
    type: 'doctrine',
    priority: 'high',
    icon: '🛡️',
    message: 'Muninn fleet detected in Tribute',
    detail: 'R1O-GN — 38 ships spotted on D-Scan',
    timestamp: now,
    link: '/war-intel',
  },
  {
    id: '3',
    type: 'manipulation',
    priority: 'medium',
    icon: '📈',
    message: 'Market anomaly: Tritanium price spike',
    detail: 'Jita sell up 23% in 2h — possible manipulation',
    timestamp: now,
    link: '/market',
  },
  {
    id: '4',
    type: 'fuel',
    priority: 'low',
    icon: '⛽',
    message: 'Raitaru fuel bay at 15%',
    detail: 'K-6K16 — estimated 4 days remaining',
    timestamp: now,
  },
  {
    id: '5',
    type: 'battle',
    priority: 'high',
    icon: '⚔️',
    message: 'IHUB reinforced in M-OEE8',
    detail: 'Timer exits in 1h 23m',
    timestamp: now,
    link: '/war-intel',
  },
  {
    id: '6',
    type: 'doctrine',
    priority: 'medium',
    icon: '🔍',
    message: 'Covert ops gang roaming Venal',
    detail: '12 Bombers, possible bridger in range',
    timestamp: now,
  },
];

export const NoAlerts: Story = {
  args: {
    alerts: [],
  },
};

export const SingleAlert: Story = {
  args: {
    alerts: [sampleAlerts[0]],
  },
};

export const CriticalAlert: Story = {
  args: {
    alerts: [sampleAlerts[0]],
    maxVisible: 3,
  },
};

export const MultipleAlerts: Story = {
  args: {
    alerts: sampleAlerts.slice(0, 3),
    maxVisible: 3,
  },
};

export const OverflowWithRotation: Story = {
  args: {
    alerts: sampleAlerts,
    maxVisible: 3,
    rotateInterval: 4000,
  },
};

export const HighPriority: Story = {
  args: {
    alerts: sampleAlerts.filter((a) => a.priority === 'high' || a.priority === 'critical'),
    maxVisible: 3,
  },
};

export const LowPriority: Story = {
  args: {
    alerts: [sampleAlerts[3]],
  },
};
