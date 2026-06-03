// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import remarkGfm from 'remark-gfm';

export default defineConfig({
  site: 'https://skills.vanducng.dev',
  markdown: { remarkPlugins: [remarkGfm] },
  integrations: [
    starlight({
      title: 'vd skills',
      description:
        'A portable skill catalog for Claude Code, Codex, and repository-local agent workflows.',
      customCss: ['./src/styles/theme.css'],
      social: [
        { icon: 'github', label: 'GitHub', href: 'https://github.com/vanducng/skills' },
      ],
      lastUpdated: true,
      sidebar: [
        { label: 'Install', items: ['install', 'getting-started'] },
        { label: 'For Agents', items: ['agent-context'] },
        { label: 'Catalog', items: ['skills', 'workflows'] },
        {
          label: 'Project',
          items: ['system-architecture', 'tech-stack', 'development-guidelines', 'deployment'],
        },
      ],
    }),
  ],
});
