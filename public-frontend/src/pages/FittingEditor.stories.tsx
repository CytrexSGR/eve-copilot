import { createElement } from 'react';
import type { Meta, StoryObj } from '@storybook/react-vite';
import type { Decorator } from '@storybook/react-vite';
import { MemoryRouter } from 'react-router-dom';
import { FittingEditor } from './FittingEditor';
import { handlers } from '../../.storybook/mocks/handlers';
import {
  mockDrakePvEItems,
  mockMuninnFleetItems,
  DRAKE_TYPE_ID,
  MUNINN_TYPE_ID,
} from '../../.storybook/mocks/data/fittings';

/**
 * Decorator that wraps the story in a MemoryRouter with a specific initial entry
 * and location.state. This inner MemoryRouter takes precedence over the global one
 * from preview.ts, ensuring useLocation() returns the correct state.
 */
function withEditorRouter(state?: Record<string, unknown>): Decorator {
  return (Story) =>
    createElement(
      MemoryRouter,
      { initialEntries: [{ pathname: '/fittings/new', state: state ?? null }] },
      createElement(Story)
    );
}

const meta: Meta<typeof FittingEditor> = {
  title: 'Fittings & Navigation/Fittings/FittingEditor',
  component: FittingEditor,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers },
    layout: 'fullscreen',
  },
};

export default meta;
type Story = StoryObj<typeof FittingEditor>;

/**
 * Empty editor — no ship selected yet. User picks a hull from the ship browser.
 */
export const NewFitting: Story = {
  decorators: [withEditorRouter()],
};

/**
 * Pre-loaded Drake PvE fitting — editor opens with ship + modules already set
 * via location.state (same mechanism as "Edit" from FittingDetail).
 */
export const EditDrake: Story = {
  decorators: [
    withEditorRouter({
      shipTypeId: DRAKE_TYPE_ID,
      items: mockDrakePvEItems,
      name: 'Drake PvE L4',
      charges: {
        27: 24517, 28: 24517, 29: 24517, 30: 24517,
        31: 24517, 32: 24517, 33: 24517,
      },
    }),
  ],
};

/**
 * Pre-loaded Muninn Fleet fitting — armor-tanked HAC with artillery.
 */
export const EditMuninn: Story = {
  decorators: [
    withEditorRouter({
      shipTypeId: MUNINN_TYPE_ID,
      items: mockMuninnFleetItems,
      name: 'Muninn Fleet Alpha',
      charges: {},
    }),
  ],
};
