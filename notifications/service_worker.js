/**
 * @fileoverview ReelTime's service worker, served at /sw.js. It shows
 * push notifications and opens their page when one is tapped. It has no
 * fetch handler, so pages always come from the server.
 */

const FALLBACK = {
  title: 'ReelTime',
  body: 'Something new on a review link.',
  path: '/',
  tag: 'reeltime',
};

/**
 * The message a push carries, or the fallback. Every push shows a
 * notification: browsers take away a subscription whose pushes don't.
 * @param {!Event} event A push event.
 * @return {{title: string, body: string, path: string, tag: string}}
 */
function read(event) {
  let data;
  try {
    data = event.data ? event.data.json() : {};
  } catch {
    return FALLBACK;
  }
  const message = {...FALLBACK};
  for (const name of Object.keys(FALLBACK)) {
    if (data && typeof data[name] === 'string' && data[name]) {
      message[name] = data[name];
    }
  }
  return message;
}

/**
 * The page to open: a path on this server, never anywhere else.
 * @param {?string|undefined} path
 * @return {string}
 */
function safeUrl(path) {
  try {
    const url = new URL(String(path), self.location.origin);
    if (url.origin === self.location.origin) {
      return url.href;
    }
  } catch {
    // Not a URL: open the start page.
  }
  return new URL('/', self.location.origin).href;
}

self.addEventListener('push', (event) => {
  const message = read(event);
  event.waitUntil(
    self.registration.showNotification(message.title, {
      body: message.body,
      tag: message.tag,
      data: {path: message.path},
    }),
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = safeUrl(event.notification.data && event.notification.data.path);
  event.waitUntil(
    (async () => {
      const open = await self.clients.matchAll({
        type: 'window',
        includeUncontrolled: true,
      });
      for (const client of open) {
        if (new URL(client.url).origin === self.location.origin) {
          await client.focus();
          try {
            await client.navigate(url);
            return;
          } catch {
            break; // not ours to steer: open a window instead
          }
        }
      }
      await self.clients.openWindow(url);
    })(),
  );
});
