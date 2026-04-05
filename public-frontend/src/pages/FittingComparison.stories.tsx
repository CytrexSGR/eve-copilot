import type { Meta, StoryObj } from '@storybook/react-vite';
import { FittingComparison } from './FittingComparison';
import { handlers } from '../../.storybook/mocks/handlers';

/**
 * FittingComparison loads custom + shared fittings via API on mount,
 * then lets the user pick 2-4 fittings from dropdowns. All data comes
 * from MSW handlers (mockCustomFittings + compareFittings endpoint).
 *
 * The global MemoryRouter from preview.ts is sufficient here since
 * the page does not use useParams().
 */
const meta: Meta<typeof FittingComparison> = {
  title: 'Fittings & Navigation/Fittings/FittingComparison',
  component: FittingComparison,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers },
    layout: 'fullscreen',
  },
};

export default meta;
type Story = StoryObj<typeof FittingComparison>;

/**
 * Default state — 3 custom fittings available in dropdowns
 * (Drake Shield Tank V2, Muninn Fleet Alpha, Vedmak Solo).
 * User selects 2+ to trigger the comparison table.
 */
export const DrakeVsMuninn: Story = {};

/**
 * Same component, ready for 3-way comparison.
 * Start with the default 2-slot view and click "+ Add" for a third slot.
 */
export const ThreeWayComparison: Story = {};
