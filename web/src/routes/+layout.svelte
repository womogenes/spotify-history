<script>
import '../app.css';
let { children } = $props();
</script>

<svelte:head>
  <!-- Title, favicon, etc. -->
  <title>Spotify History Visualizer</title>
  <link
    rel="icon"
    href="https://storage.googleapis.com/pr-newsroom-wp/1/2023/05/Spotify_Primary_Logo_RGB_Black.png"
  />

  <!-- Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link
    href="https://fonts.googleapis.com/css2?family=Fira+Mono:wght@400;500;700&family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&display=swap"
    rel="stylesheet"
  />
</svelte:head>

<div class="dark:dark h-full bg-white dark:bg-neutral-950">
  {@render children?.()}
</div>

<style>
:global(html, body) {
  @apply h-full;
}
</style>
