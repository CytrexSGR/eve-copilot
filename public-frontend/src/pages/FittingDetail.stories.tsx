import { createElement } from 'react';
import type { Meta, StoryObj } from '@storybook/react-vite';
import type { Decorator } from '@storybook/react-vite';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { FittingDetail } from './FittingDetail';
import { handlers } from '../../.storybook/mocks/handlers';

/**
 * Decorator that wraps the story in a MemoryRouter with Routes,
 * so that useParams() returns the correct fittingId. The inner router
 * takes precedence over the global one from preview.ts.
 */
function withDetailRouter(fittingId: number, prefix: 'custom' | 'esi' = 'custom'): Decorator {
  return () =>
    createElement(
      MemoryRouter,
      { initialEntries: [`/fittings/${prefix}/${fittingId}`] },
      createElement(
        Routes,
        null,
        createElement(Route, {
          path: `/fittings/${prefix}/:fittingId`,
          element: createElement(FittingDetail),
        })
      )
    );
}

const meta: Meta<typeof FittingDetail> = {
  title: 'Fittings & Navigation/Fittings/FittingDetail',
  component: FittingDetail,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers },
    layout: 'fullscreen',
  },
};

export default meta;
type Story = StoryObj<typeof FittingDetail>;

/**
 * Drake Shield Tank V2 — Custom fitting with charges, PvE/Solo tags.
 * Uses custom fitting id 2001 from mock data.
 */
export const DrakeDetail: Story = {
  decorators: [withDetailRouter(2001, 'custom')],
};

/**
 * Muninn Fleet Alpha — Custom fitting, armor-tanked HAC for fleet use.
 * Uses custom fitting id 2002 from mock data.
 */
export const MuninnDetail: Story = {
  decorators: [withDetailRouter(2002, 'custom')],
};
