import type { Meta, StoryObj } from '@storybook/react';
import { SectionCard } from './SectionCard';

const meta: Meta<typeof SectionCard> = {
  title: 'Corp/Dashboard/SectionCard',
  component: SectionCard,
  parameters: { layout: 'padded' },
};
export default meta;
type Story = StoryObj<typeof SectionCard>;

export const Default: Story = {
  args: {
    title: 'Military Overview',
    borderColor: '#f85149',
    linkTo: '/corp/military',
    children: (
      <div style={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.8rem' }}>
        <div>K/D Ratio: 3.44</div>
        <div>ISK Efficiency: 77.5%</div>
        <div>Active Pilots: 142</div>
      </div>
    ),
  },
};

export const Loading: Story = {
  args: {
    title: 'Treasury',
    borderColor: '#3fb950',
    linkTo: '/corp/finance',
    loading: true,
    children: null,
  },
};

export const CustomLinkLabel: Story = {
  args: {
    title: 'SRP Requests',
    borderColor: '#d29922',
    linkTo: '/corp/srp',
    linkLabel: 'Manage SRP',
    children: (
      <div style={{ color: '#d29922', fontSize: '0.85rem', fontWeight: 700 }}>
        5 pending requests
      </div>
    ),
  },
};
