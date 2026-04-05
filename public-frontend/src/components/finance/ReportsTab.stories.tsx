import type { Meta, StoryObj } from '@storybook/react';
import { ReportsTab } from './ReportsTab';
import { financeHandlers } from '../../../.storybook/mocks/handlers/finance';

const meta: Meta<typeof ReportsTab> = {
  title: 'Corporation Tools/Finance/ReportsTab',
  component: ReportsTab,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers: financeHandlers },
  },
};
export default meta;
type Story = StoryObj<typeof ReportsTab>;

export const Default: Story = {
  args: {
    corpId: 98378388,
  },
};
