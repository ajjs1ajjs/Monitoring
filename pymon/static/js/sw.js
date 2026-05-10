const CACHE_NAME = 'pymon-v1';
const ASSETS = [
  '/',
  '/static/css/dashboard.css',
  '/static/js/dashboard.js',
  'https://unpkg.com/lucide@latest',
  'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.min.js'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});
