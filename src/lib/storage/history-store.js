import { browser } from '$app/environment';

const STREAMING_HISTORY_KEY = 'streaming_history';

export async function loadStreamingHistory() {
  if (!browser) return [];

  const { get } = await import('idb-keyval');
  return (await get(STREAMING_HISTORY_KEY)) ?? [];
}

export async function saveStreamingHistory(history) {
  if (!browser) return;

  const { set } = await import('idb-keyval');
  await set(STREAMING_HISTORY_KEY, history);
}
