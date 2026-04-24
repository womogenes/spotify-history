import adapter from '@sveltejs/adapter-auto';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

const config = {
  kit: {
    adapter: adapter(),
    alias: { lib: './src/lib' }
  },
  preprocess: vitePreprocess()
};
export default config;
