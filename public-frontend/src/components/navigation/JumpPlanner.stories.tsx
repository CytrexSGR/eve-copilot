import type { Meta, StoryObj } from '@storybook/react';
import { JumpPlanner } from './JumpPlanner';
import { fittingsHandlers } from '../../../.storybook/mocks/handlers/fittings';

const meta: Meta<typeof JumpPlanner> = {
  title: 'Fittings & Navigation/Navigation/JumpPlanner',
  component: JumpPlanner,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers: fittingsHandlers },
  },
};
export default meta;
type Story = StoryObj<typeof JumpPlanner>;

export const Default: Story = {};
