import type { Meta, StoryObj } from '@storybook/react';
import { ActivityTab } from './ActivityTab';
import { financeHandlers } from '../../../.storybook/mocks/handlers/finance';

const meta: Meta<typeof ActivityTab> = {
  title: 'Corporation Tools/HR/ActivityTab',
  component: ActivityTab,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers: financeHandlers },
  },
};
export default meta;
type Story = StoryObj<typeof ActivityTab>;

export const Default: Story = {
  args: {
    corpId: 98378388,
  },
};
