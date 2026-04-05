import type { Meta, StoryObj } from '@storybook/react';
import FighterSection from './FighterSection';
import { fittingsHandlers } from '../../../.storybook/mocks/handlers/fittings';
import { fn } from '@storybook/test';

const meta: Meta<typeof FighterSection> = {
  title: 'Fittings & Navigation/Fittings/FighterSection',
  component: FighterSection,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers: fittingsHandlers },
  },
  args: {
    onFightersChange: fn(),
  },
};
export default meta;
type Story = StoryObj<typeof FighterSection>;

export const WithFighters: Story = {
  args: {
    fighters: [
      { type_id: 40556, quantity: 3 },
      { type_id: 40557, quantity: 2 },
    ],
  },
};

export const EmptyFighterBay: Story = {
  args: {
    fighters: [],
  },
};
