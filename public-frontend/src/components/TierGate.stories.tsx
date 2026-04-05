import type { Meta, StoryObj } from '@storybook/react';
import { TierGate } from './TierGate';

const meta: Meta<typeof TierGate> = {
  title: 'Shared UI/TierGate',
  component: TierGate,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof TierGate>;

export const Default: Story = {
  args: {
    requiredTier: 'free',
    children: (
      <div style={{ padding: '1rem', background: 'rgba(0, 212, 255, 0.1)', borderRadius: '8px', color: '#fff' }}>
        Free tier content — visible to all users. Basic intel dashboard with public killboard data.
      </div>
    ),
  },
};

export const PilotTier: Story = {
  args: {
    requiredTier: 'pilot',
    children: (
      <div style={{ padding: '1rem', background: 'rgba(0, 255, 136, 0.1)', borderRadius: '8px', color: '#fff' }}>
        Pilot tier content — Market analysis, production calculator, fitting editor.
      </div>
    ),
  },
};

export const CorporationTier: Story = {
  args: {
    requiredTier: 'corporation',
    children: (
      <div style={{ padding: '1rem', background: 'rgba(255, 136, 0, 0.1)', borderRadius: '8px', color: '#fff' }}>
        Corporation tier content — Corp finance, mining tax dashboard, SRP management.
      </div>
    ),
  },
};

export const CoalitionTier: Story = {
  args: {
    requiredTier: 'coalition',
    children: (
      <div style={{ padding: '1rem', background: 'rgba(255, 204, 0, 0.1)', borderRadius: '8px', color: '#fff' }}>
        Coalition tier content — PowerBloc intelligence, cross-alliance fleet tools, strategic mapping.
      </div>
    ),
  },
};

export const WithPreview: Story = {
  args: {
    requiredTier: 'corporation',
    showPreview: true,
    children: (
      <div style={{ padding: '1rem', background: 'rgba(255, 136, 0, 0.1)', borderRadius: '8px', color: '#fff' }}>
        Corporation content shown in preview mode — user can see the content but cannot interact.
      </div>
    ),
  },
};
