// Query for top n tracks in a time range
export let songDetails = new Map();

const lowerBound = (history, ts: number) => {
  let n = history.length;
  let lo = 0,
    hi = n - 1;
  while (hi > lo) {
    let mid = (lo + hi) >> 1;
    if (history[mid].ts >= ts) {
      hi = mid;
    } else {
      lo = mid + 1;
    }
  }
  return lo;
};

export const getSongPopularity = (history, startTime: number, endTime: number) => {
  const startIdx = lowerBound(history, startTime);
  const endIdx = lowerBound(history, endTime + 1);
  const msListenedTo = new Map();
  for (let i = startIdx; i <= endIdx; i++) {
    const { ms_played, track_uri: uri } = history[i];
    msListenedTo.set(uri, (msListenedTo.get(uri) ?? 0) + ms_played);

    // Cache song details
    if (!songDetails.has(uri)) {
      songDetails.set(uri, {
        track_name: history[i].track_name,
        artist_name: history[i].artist_name,
        album_name: history[i].album_name,
        track_uri: uri
      });
    }
  }

  return Array.from(msListenedTo)
    .sort((a, b) => -(a[1] - b[1]))
    .filter(([uri, _]) => uri && songDetails.has(uri))
    .map(([uri, duration]) => [songDetails.get(uri), duration])
    .slice(0, 10);
};
