import type { Meta, StoryObj } from '@storybook/react';
import { DoctrinesTab } from './DoctrinesTab';
import { financeHandlers } from '../../../.storybook/mocks/handlers/finance';

const meta: Meta<typeof DoctrinesTab> = {
  title: 'Corporation Tools/SRP/DoctrinesTab',
  component: DoctrinesTab,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers: financeHandlers },
  },
};
export default meta;
type Story = StoryObj<typeof DoctrinesTab>;

export const Default: Story = {
  args: {
    corpId: 98378388,
  },
};
