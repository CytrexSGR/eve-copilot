import type { StorybookConfig } from '@storybook/react-vite';

const config: StorybookConfig = {
  stories: [
    '../src/stories/**/*.mdx',
    '../src/**/*.stories.@(ts|tsx)',
  ],
  addons: [
    '@storybook/addon-docs',
    '@storybook/addon-a11y',
    '@storybook/addon-vitest',
  ],
  framework: '@storybook/react-vite',
  staticDirs: ['../public'],
  docs: {
    autodocs: 'tag',
  },
  viteFinal: async (config) => {
    if (config.server) {
      delete config.server.proxy;
    }
    return config;
  },
};

export default config;
