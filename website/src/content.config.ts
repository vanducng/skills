import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { docsSchema } from '@astrojs/starlight/schema';

// Authored content lives in website/docs/ (diagrams/ holds generated artifacts, not pages).
export const collections = {
  docs: defineCollection({
    loader: glob({ pattern: ['**/[^_]*.{md,mdx}', '!diagrams/**'], base: './docs' }),
    schema: docsSchema(),
  }),
};
