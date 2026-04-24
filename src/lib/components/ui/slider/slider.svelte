<script>
import { cn } from '$lib/utils.js';

let {
  class: className = undefined,
  value = $bindable([0]),
  min = 0,
  max = 100,
  step = 1,
  type = 'range',
  ...rest
} = $props();

const handleInput = (event) => {
  value = [Number(event.currentTarget.value)];
};
</script>

<input
  type={type}
  min={min}
  max={max}
  step={step}
  class={cn(
    'slider h-2 w-full cursor-pointer appearance-none rounded-full bg-neutral-200 dark:bg-neutral-800',
    className
  )}
  value={value[0] ?? min}
  oninput={handleInput}
  {...rest}
/>

<style>
.slider::-webkit-slider-thumb {
  appearance: none;
  width: 1rem;
  height: 1rem;
  border-radius: 9999px;
  background: white;
  border: 2px solid black;
}

.slider::-moz-range-thumb {
  width: 1rem;
  height: 1rem;
  border-radius: 9999px;
  background: white;
  border: 2px solid black;
}
</style>
