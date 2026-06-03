// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import react from '@astrojs/react';
import starlightLlmsTxt from 'starlight-llms-txt';
import remarkGfm from 'remark-gfm';

export default defineConfig({
  site: 'https://skills.vanducng.dev',
  // GFM (tables, strikethrough) for MDX — .mdx does not get it by default.
  // NOTE: markdown.remarkPlugins is deprecated in Astro 6; migrate when bumping major.
  markdown: { remarkPlugins: [remarkGfm] },
  integrations: [
    starlight({
      title: 'skills',
      description:
        'A portable skill catalog for Claude Code, Codex, and repository-local agent workflows.',
      customCss: ['./src/styles/theme.css'],
      expressiveCode: {
        themes: ['catppuccin-mocha', 'catppuccin-latte'],
        styleOverrides: { borderRadius: '0.5rem' },
      },
      components: {
        ThemeSelect: './src/components/ThemeSelect.astro',
        SocialIcons: './src/components/SocialIcons.astro',
        Search: './src/components/Search.astro',
      },
      plugins: [
        starlightLlmsTxt({
          projectName: 'vd skills',
          description:
            'A portable skill catalog for Claude Code, Codex, and repository-local agent workflows.',
        }),
      ],
      lastUpdated: true,
      sidebar: [
        { label: 'Overview', link: '/' },
        { label: 'Install', items: ['install', 'getting-started'] },
        { label: 'For Agents', items: ['agent-context'] },
        { label: 'Catalog', items: ['skills', 'workflows'] },
        {
          label: 'Project',
          items: ['tech-stack', 'development-guidelines', 'deployment'],
        },
      ],
    }),
    react(),
  ],
});
