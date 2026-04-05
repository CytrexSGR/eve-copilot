import type { Meta, StoryObj } from '@storybook/react';
import { EfficiencyBar } from './EfficiencyBar';

const meta: Meta<typeof EfficiencyBar> = {
  title: 'Doctrines/EfficiencyBar',
  component: EfficiencyBar,
  parameters: { layout: 'centered' },
  decorators: [(Story) => (
    <div style={{ width: 300 }}><Story /></div>
  )],
};
export default meta;
type Story = StoryObj<typeof EfficiencyBar>;

export const HighEfficiency: Story = {
  args: {
    value: 1.87,
    label: 'ISK Eff',
  },
};

export const EvenEfficiency: Story = {
  args: {
    value: 1.0,
    label: 'ISK Eff',
  },
};

export const LowEfficiency: Story = {
  args: {
    value: 0.45,
    label: 'ISK Eff',
  },
};

export const NoPercent: Story = {
  args: {
    value: 2.34,
    label: 'K/D',
    showPercent: false,
  },
};
