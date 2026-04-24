// PLAYBACK ENDPOINT DOES NOT WORK YET
// Need to implement authorization code flow:
//   https://developer.spotify.com/documentation/web-api/tutorials/code-flow

import { SPOTIFY_API_TOKEN } from '../spotifyApi';

export async function PUT({ url, request }) {
  const trackUri = url.searchParams.get('track-uri');

  const res = await fetch('https://api.spotify.com/v1/me/player/play', {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      Authorization: `Bearer ${SPOTIFY_API_TOKEN}`
    },
    body: JSON.stringify({
      context_uri: trackUri,
      position_ms: 0
    })
  });

  return new Response(null, { status: 204 });
}
