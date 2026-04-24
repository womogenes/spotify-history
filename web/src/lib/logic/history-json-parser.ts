export const parseHistoryJSON = (json: string) => {
  return JSON.parse(json).map((stream) => ({
    ts: new Date(stream.ts).getTime(),
    ms_played: stream.ms_played,
    track_name: stream.master_metadata_track_name,
    artist_name: stream.master_metadata_album_artist_name,
    album_name: stream.master_metadata_album_album_name,
    track_uri: stream.spotify_track_uri
  }));
};

// Merge old streaming history with new streaming history
// Don't add streams that already exist in old streamsd
export const mergeHistory = (oldHistory, addHistory) => {
  const oldIdSet = new Set(oldHistory.map((stream) => stream.ts));
  const newHistoryToAdd = addHistory.filter((stream) => !oldIdSet.has(stream.ts));
  const newHistory = [...oldHistory, ...newHistoryToAdd];
  newHistory.sort((a, b) => (a.ts < b.ts ? -1 : 1));
  return newHistory;
};
