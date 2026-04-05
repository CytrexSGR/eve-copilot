import type { Meta, StoryObj } from '@storybook/react-vite';
import { http, HttpResponse } from 'msw';
import { Fittings } from './Fittings';
import { handlers } from '../../.storybook/mocks/handlers';

const meta: Meta<typeof Fittings> = {
  title: 'Fittings & Navigation/Fittings/FittingsBrowser',
  component: Fittings,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers },
    layout: 'fullscreen',
  },
};

export default meta;
type Story = StoryObj<typeof Fittings>;

/**
 * Default view — shows "My Fits" tab with 3 ESI fittings
 * (Drake PvE L4, Muninn Fleet, Gila Abyss T4). The "Shared Fits"
 * tab shows 3 custom fittings. Global MemoryRouter from preview.ts
 * is sufficient since this page doesn't use useParams().
 */
export const Default: Story = {};

/**
 * Empty shared fittings tab — overrides the shared fittings handler
 * to return an empty array, simulating no community fittings available.
 */
export const EmptyShared: Story = {
  parameters: {
    msw: {
      handlers: [
        ...handlers,
        // Override the shared fittings endpoint to return empty
        http.get('/api/fittings/shared', () => {
          return HttpResponse.json([]);
        }),
      ],
    },
  },
};
