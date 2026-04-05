import type { Meta, StoryObj } from '@storybook/react';
import { PapStatsTab } from './PapStatsTab';
import { financeHandlers } from '../../../.storybook/mocks/handlers/finance';

const meta: Meta<typeof PapStatsTab> = {
  title: 'Corporation Tools/Fleet/PapStatsTab',
  component: PapStatsTab,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers: financeHandlers },
  },
};
export default meta;
type Story = StoryObj<typeof PapStatsTab>;

export const Default: Story = {
  args: {
    corpId: 98378388,
  },
};
