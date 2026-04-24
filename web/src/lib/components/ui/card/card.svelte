<script>
import { cn } from '$lib/utils.js';
let { class: className = undefined, children, ...rest } = $props();
</script>

<div class={cn('rounded-lg border shadow-sm dark:bg-neutral-900/40', className)} {...rest}>
  {@render children?.()}
</div>
