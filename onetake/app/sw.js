// One Take as a home-screen app. Nothing is cached (the studio must always show the latest edit);
// this only lets the phone install it and shows a friendly page when the Chromebook can't be reached.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", (e) => {
  if (e.request.mode !== "navigate") return;  // videos, API calls etc. go straight to the studio
  e.respondWith(fetch(e.request).catch(() => new Response(
    '<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1">' +
    '<body style="font-family:sans-serif;background:#121217;color:#eee;display:grid;place-items:center;height:100vh;margin:0;text-align:center">' +
    '<div><div style="font-size:48px">✂</div><h2>One Take can\'t reach your Chromebook</h2>' +
    '<p>Check it\'s on, plugged in and connected to Wi-Fi, then pull down to try again.</p></div>',
    {headers: {"Content-Type": "text/html; charset=utf-8"}})));
});
