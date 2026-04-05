import type { Meta, StoryObj } from '@storybook/react';
import { AlertPanel } from './AlertPanel';
import type { Alert } from '../../types/alerts';
import { fn } from '@storybook/test';

const meta: Meta<typeof AlertPanel> = {
  title: 'Alerts/AlertPanel',
  component: AlertPanel,
  parameters: { layout: 'centered' },
};
export default meta;
type Story = StoryObj<typeof AlertPanel>;

const mockAlerts: Alert[] = [
  {
    id: '1',
    type: 'intel',
    severity: 'urgent',
    title: 'Capital Fleet Spotted',
    message: 'Titan and 3 supers spotted in K-6K16',
    timestamp: new Date(),
    actionUrl: '/alliance/99003581',
    dismissed: false,
  },
  {
    id: '2',
    type: 'market',
    severity: 'warning',
    title: 'Price Spike: Tritanium',
    message: 'Tritanium price up 15% in Jita in the last hour',
    timestamp: new Date(),
    actionUrl: '/market',
    dismissed: false,
  },
  {
    id: '3',
    type: 'industry',
    severity: 'info',
    title: 'Job Complete',
    message: 'Manufacturing job for 10x Drake finished',
    timestamp: new Date(),
    dismissed: false,
  },
  {
    id: '4',
    type: 'corp',
    severity: 'warning',
    title: 'SRP Pending',
    message: '3 SRP requests awaiting review',
    timestamp: new Date(),
    actionUrl: '/corp/srp',
    dismissed: false,
  },
];

export const WithAlerts: Story = {
  args: {
    alerts: mockAlerts,
    onDismiss: fn(),
    onDismissAll: fn(),
    onClose: fn(),
  },
};

export const Empty: Story = {
  args: {
    alerts: [],
    onDismiss: fn(),
    onDismissAll: fn(),
    onClose: fn(),
  },
};

export const AllDismissed: Story = {
  args: {
    alerts: mockAlerts.map(a => ({ ...a, dismissed: true })),
    onDismiss: fn(),
    onDismissAll: fn(),
    onClose: fn(),
  },
};

export const SingleAlert: Story = {
  args: {
    alerts: [mockAlerts[0]],
    onDismiss: fn(),
    onDismissAll: fn(),
    onClose: fn(),
  },
};
