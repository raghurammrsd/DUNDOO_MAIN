const CACHE_NAME = 'dundoo-cache-v1';
const urlsToCache = [
  '/static/css/styles.css',
  '/static/css/user.css',
  '/static/js/voice_assistant.js',
  '/static/js/tilt.js'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) {
          return response;
        }
        return fetch(event.request);
      })
  );
});
