import type { Meta, StoryObj } from '@storybook/react';
import { RedListTab } from './RedListTab';
import { financeHandlers } from '../../../.storybook/mocks/handlers/finance';

const meta: Meta<typeof RedListTab> = {
  title: 'Corporation Tools/HR/RedListTab',
  component: RedListTab,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers: financeHandlers },
  },
};
export default meta;
type Story = StoryObj<typeof RedListTab>;

export const Default: Story = {
  args: {
    corpId: 98378388,
  },
};
