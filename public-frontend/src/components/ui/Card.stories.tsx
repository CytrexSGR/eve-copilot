import type { Meta, StoryObj } from '@storybook/react';
import { Card, CardHeader, CardLink } from './Card';

// ---------------------------------------------------------------------------
// Card
// ---------------------------------------------------------------------------

const cardMeta: Meta<typeof Card> = {
  title: 'Shared UI/Card',
  component: Card,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
  argTypes: {
    variant: {
      control: 'select',
      options: ['default', 'danger', 'accent', 'warning'],
    },
    padding: {
      control: 'select',
      options: ['none', 'sm', 'md', 'lg'],
    },
    withNoise: { control: 'boolean' },
  },
};

export default cardMeta;
type CardStory = StoryObj<typeof Card>;

export const Default: CardStory = {
  args: {
    children: 'Fleet status nominal. All pilots on standby.',
  },
};

export const Danger: CardStory = {
  args: {
    variant: 'danger',
    children: 'ALERT: Hostile fleet detected in K-6K16 — 47 Muninns on gate.',
  },
};

export const Accent: CardStory = {
  args: {
    variant: 'accent',
    children: 'Wormhole C5-C5 chain mapped. Estimated ISK: 2.4B in anomalies.',
  },
};

export const Warning: CardStory = {
  args: {
    variant: 'warning',
    children: 'Fuel bay at 12%. Estimated depletion in 3 days.',
  },
};

export const NoPadding: CardStory = {
  args: {
    padding: 'none',
    children: 'Card with no padding for custom layouts.',
  },
};

export const SmallPadding: CardStory = {
  args: {
    padding: 'sm',
    children: 'Card with small padding.',
  },
};

export const LargePadding: CardStory = {
  args: {
    padding: 'lg',
    children: 'Card with large padding for spacious content.',
  },
};

export const WithoutNoise: CardStory = {
  args: {
    withNoise: false,
    children: 'Clean card without noise texture overlay.',
  },
};

// ---------------------------------------------------------------------------
// CardHeader
// ---------------------------------------------------------------------------

export const HeaderDefault: StoryObj<typeof CardHeader> = {
  render: (args) => (
    <Card>
      <CardHeader {...args} />
      <div style={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.85rem' }}>
        Real-time intelligence feed from zKillboard and ESI data.
      </div>
    </Card>
  ),
  args: {
    icon: '🛡️',
    title: 'Fleet Intelligence',
    subtitle: 'Last 24 hours',
  },
};

export const HeaderWithAction: StoryObj<typeof CardHeader> = {
  render: (args) => (
    <Card variant="accent">
      <CardHeader
        {...args}
        action={<CardLink to="/war-intel">View All</CardLink>}
      />
      <div style={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.85rem' }}>
        3 active sov campaigns detected in Tribute.
      </div>
    </Card>
  ),
  args: {
    icon: '⚔️',
    title: 'Active Campaigns',
    subtitle: 'Sovereignty timers',
    titleColor: '#00d4ff',
  },
};

export const HeaderNoIcon: StoryObj<typeof CardHeader> = {
  render: (args) => (
    <Card>
      <CardHeader {...args} />
      <div style={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.85rem' }}>
        Jita buy: 1,245.32 ISK | Amarr sell: 1,312.50 ISK
      </div>
    </Card>
  ),
  args: {
    title: 'Market Prices',
    subtitle: 'Tritanium',
  },
};

// ---------------------------------------------------------------------------
// CardLink
// ---------------------------------------------------------------------------

export const LinkDefault: StoryObj<typeof CardLink> = {
  render: () => (
    <Card>
      <CardHeader
        icon="📊"
        title="Corporation Overview"
        subtitle="Fraternity."
        action={<CardLink to="/corporation/98378388">Details</CardLink>}
      />
    </Card>
  ),
};
