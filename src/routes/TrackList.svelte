<script>
import { Slider } from '$lib/components/ui/slider';
import { getSongPopularity } from '$lib/logic/summary';
import { formatTimestamp } from '$lib/logic/utils';
import TrackItem from 'lib/components/TrackItem.svelte';
import { flip } from 'svelte/animate';
import { fade, slide } from 'svelte/transition';

let { history = [] } = $props();

let minTime = $state(0);
let maxTime = $state(0);
let queryRange = $state(3600 * 24 * 7 * 1000);
let sliderTimeValue = $state([0]);
let sliderTime = $derived(sliderTimeValue[0] * 1e3 + minTime);
let songPopularity = $derived.by(() => {
  return getSongPopularity(history, sliderTime - queryRange, sliderTime);
});

$effect(() => {
  minTime = history[0].ts;
  maxTime = history[history.length - 1].ts;
  sliderTimeValue = [(maxTime - minTime) / 1e3]; // Jump to end of history
});
</script>

<div class="mx-auto flex h-full w-full max-w-4xl flex-col gap-1 overflow-x-auto">
  <div class="mb-2 mt-2 flex flex-col">
    <div class="mx-3">
      <Slider
        type="range"
        class="mb-2 w-full"
        bind:value={sliderTimeValue}
        min={0}
        max={(maxTime - minTime) / 1e3}
        step={3600 * 24}
      />
      <div class="text-muted flex justify-between">
        <p>{formatTimestamp(minTime)}</p>
        <p>{formatTimestamp(maxTime)}</p>
      </div>
    </div>
    <p class="mx-auto mb-1">Top songs in range:</p>
    <p class="mx-auto text-4xl font-bold tabular-nums">
      {formatTimestamp(sliderTime - queryRange)}
      &ndash;
      {formatTimestamp(sliderTime)}
    </p>
  </div>

  <div class="h-full overflow-y-auto py-2">
    <!-- List container -->
    <div class="flex flex-col gap-2">
      {#each songPopularity as [track, ms], index (track.track_uri)}
        <div style={`z-index: ${1000 - 100 * index}`}>
          <TrackItem track={track} ms={ms} />
        </div>
      {/each}
    </div>
  </div>
</div>
