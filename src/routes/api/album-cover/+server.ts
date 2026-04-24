import { error, json } from '@sveltejs/kit';
import { SPOTIFY_API_TOKEN } from '../spotifyApi';

// Endpoint to get the album cover URL
// Some fancy stuff is needed to avoid rate limits

export async function GET({ url, setHeaders, request }) {
  const trackId = url.searchParams.get('track-id') || '';

  let res: Response;
  while (true) {
    res = await fetch(`https://api.spotify.com/v1/tracks/${trackId}`, {
      headers: {
        Authorization: `Bearer ${SPOTIFY_API_TOKEN}`
      }
    });
    if (res.status === 200) {
      // We got the info, break out
      break;
    }
    if (res.status === 401 || res.status === 403) {
      return error(res.status, 'Internal server error');
    }
    if (res.status === 429) {
      // Else, res.status is 429 and we should wait
      const retryAfter = parseInt(res.headers.get('Retry-After'));
      await new Promise((r) => setTimeout(r, retryAfter * 1000));
    }
  }

  setHeaders({
    'cache-control': 'max-age=3600'
  });

  return new Response((await res.json()).album.images[0].url);
}
