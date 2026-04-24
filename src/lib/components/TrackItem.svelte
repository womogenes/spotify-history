<script>
import { formatDuration } from 'lib/logic/utils';
import { onMount } from 'svelte';
import { colorThief, rgb2hsl } from 'lib/utils';
import { trackCache } from 'lib/stores';

let { track, ms } = $props();

// Fetch album cover URL from server
let trackId = $derived(track.track_uri.split(':').pop());
let albumCoverUrl = $state('');

// On image load, compute average color
let color = $state(`0%, 0%, 20%`);
let albumCoverEl;

// Load these values from store if they exist
$effect(() => {
  const cachedTrack = $trackCache[`track_${trackId}`];
  if (cachedTrack) {
    albumCoverUrl = cachedTrack[0];
    color = cachedTrack[1];
  }
});

onMount(async () => {
  // Fetch album cover
  try {
    if (albumCoverUrl === '') {
      albumCoverUrl = await (await fetch(`/api/album-cover?track-id=${trackId}`)).text();
      trackCache.update((x) => ({ ...x, [`track_${trackId}`]: [albumCoverUrl, color] }));
    }
  } catch {
    console.log('Error fetching album cover');
  }

  // Compute average color
  if (!albumCoverEl) return;
  albumCoverEl.crossOrigin = 'Anonymous';
  albumCoverEl.onload = () => {
    // Need a try-catch because sometimes colorthief throws a fit
    try {
      let [r, g, b] = colorThief.getColor(albumCoverEl);
      let [h, s, l] = rgb2hsl(r / 255, g / 255, b / 255);
      [h, s, l] = [h, s, h >= 45 && h <= 75 ? Math.min(l, 0.35) : Math.min(l, 0.55)];
      s = Math.min(s, 0.3);
      color = `${h} ${s * 100}% ${l * 100}`;
      trackCache.update((x) => ({ ...x, [`track_${trackId}`]: [albumCoverUrl, color] }));
    } catch {
      return;
    }
  };
});
</script>

<a
  class="flex h-16 items-stretch overflow-hidden rounded-md text-white dark:text-white"
  href={`spotify:track:${trackId}`}
>
  <!-- Image -->
  <div
    class="flex w-16 shrink-0 cursor-pointer items-center justify-center rounded-l-md"
    style={`background-color: hsl(${color})`}
  >
    <img
      bind:this={albumCoverEl}
      width={64}
      height={64}
      src={albumCoverUrl}
      alt={track.album_name}
    />
  </div>

  <div class="relative flex h-full grow items-center gap-4 rounded-r-md bg-neutral-500 py-2">
    <!-- Length -->
    <div
      class="absolute h-full"
      style={`
        width: 100%;
        background-color: hsl(${color});
      `}
    ></div>

    <!-- Track info -->
    <div class="z-10 px-4">
      <p class="line-clamp-1 font-bold">{track.track_name}</p>
      <p class="text-muted-dark text-nowrap text-sm">{track.artist_name}</p>
    </div>

    <!-- Track listening-to duration -->
    <div class="z-10 my-auto ml-auto mr-2 px-4 tabular-nums">{formatDuration(ms)}</div>
  </div>
</a>
