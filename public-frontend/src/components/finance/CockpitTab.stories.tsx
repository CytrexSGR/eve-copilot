import type { Meta, StoryObj } from '@storybook/react';
import { CockpitTab } from './CockpitTab';
import { financeHandlers } from '../../../.storybook/mocks/handlers/finance';

const meta: Meta<typeof CockpitTab> = {
  title: 'Corporation Tools/Finance/CockpitTab',
  component: CockpitTab,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers: financeHandlers },
  },
};
export default meta;
type Story = StoryObj<typeof CockpitTab>;

export const Default: Story = {
  args: {
    corpId: 98378388,
  },
};
