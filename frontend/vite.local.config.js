// Local-only Vite dev-server override for the volteo-local docker stack.
//
// NOT part of the tracked build (untracked in git, never imported by
// vite.config.js) — this exists purely so `yarn dev` can point at
// ~/Documents/volteo-local instead of a real bench dev server, without
// touching the app's tracked vite.config.js.
//
// Why this file is needed: frappe-ui's `frappeProxy` plugin (see
// node_modules/frappe-ui/vite/frappeProxy.js) derives BOTH the Vite
// dev-server port AND its proxy target from a single `webserver_port`
// value — normally read from the bench's sites/common_site_config.json,
// which doesn't exist in this checkout (it isn't a real bench), so it
// falls back to a hardcoded default of 8000, giving a default dev port of
// 8080. It also computes the *per-request* proxy target dynamically from
// the incoming browser request's own Host header via a `router()`
// function, which overrides whatever static `target` is configured.
//
// The volteo-local stack's nginx (backend+frontend combined) already
// occupies host port 8080, so this dev server must run on a different
// port (8081) while still proxying API/websocket calls upstream to port
// 8080 with `Host: crm.localhost` forced — Frappe routes sites by Host
// header, and plain "localhost" 404s (only "crm.localhost" resolves to
// the restored site).
//
// Merely returning `{ server: { port, proxy } }` from this file's own
// config function is NOT enough: Vite calls every plugin's own `config()`
// hook AFTER resolving the user config, merging each result on top of
// what came before, in plugin-array order. frappeProxy is a plugin in
// that array (inserted via `config.plugins.unshift(frappeui(...))` in
// vite.config.js), so its `config()` hook runs and re-applies port 8080 +
// its own proxy, clobbering a plain object override. The fix is to append
// (push, not unshift) one more plugin whose `config()` hook runs last and
// therefore wins.
//
// Second, unrelated, pre-existing bug worked around below: reproduced with
// the tracked vite.config.js too (no override, different scratch port), so
// it is NOT caused by this file. `yarn dev`'s esbuild dependency SCANNER
// (the pre-bundling pass that runs on first real page/module request, not
// `vite build`, which succeeds cleanly) cannot resolve the virtual
// `~icons/lucide/*` imports in node_modules/frappe-ui/src/components/
// TextEditor/commands.js — frappe-ui ships raw source, and its custom
// resolver for those ids (frappe-ui/vite/lucideIcons.js) apparently isn't
// reachable from the scanner's limited esbuild plugin, only from the
// normal dev-server request pipeline. The scanner's unresolved-import
// error is an uncaught exception that kills the whole `node` process, not
// a soft warning — every request after the first one that touches that
// module graph 502s permanently. Excluding frappe-ui from dependency
// pre-bundling sidesteps the scanner entirely; it's then transformed
// on-demand through the normal pipeline, where the resolver works.
//
// Usage:
//   ./node_modules/.bin/vite --config vite.local.config.js
import base from './vite.config.js'

const CRM_LOCAL_TARGET = 'http://crm.localhost:8080'
const CRM_LOCAL_DEV_PORT = 8081

export default async (env) => {
  const config = await base(env)

  config.plugins.push({
    name: 'crm-local-dev-proxy-override',
    config: () => ({
      server: {
        port: CRM_LOCAL_DEV_PORT,
        strictPort: true,
        // Nasłuch dwustosowy. Bez `host` Vite bierze domyślny `localhost`, a Node
        // od wersji 17 rozwiązuje nazwy w kolejności "verbatim" (`::1` przed
        // `127.0.0.1`), więc serwer przypina się WYŁĄCZNIE do pętli IPv6. Safari
        // trafia wtedy na `::1` i działa, ale przeglądarki na silniku Chromium
        // (Opera, Chrome) idą dla `*.localhost` po IPv4 i dostają odmowę
        // połączenia — objaw: "serwer lokalny nie działa" w jednej przeglądarce
        // i działa w drugiej.
        // `'::'` daje nasłuch dwustosowy (Node ma domyślnie `ipv6Only=false`),
        // więc odpowiada zarówno `127.0.0.1`, jak i `[::1]`.
        // NIE używać `'0.0.0.0'` ani `host: true` — dają nasłuch wyłącznie IPv4
        // i zepsują Safari.
        // Świadoma konsekwencja: `'::'` nasłuchuje na wszystkich interfejsach,
        // więc port 8081 jest widoczny w sieci lokalnej. Nie zmienia to stanu
        // bezpieczeństwa tego stosu — kontener `frontend` już publikuje
        // `0.0.0.0:8080` i `[::]:8080` z dokładnie tymi samymi danymi.
        host: '::',
        proxy: {
          // Socket.IO: the browser connects to the dev origin (same host:port
          // as the page) and this proxies the websocket upstream to the
          // realtime server on :9000. socket.js appends `/${siteName}` before
          // `/socket.io/`, so match that optional prefix and strip it — the
          // node server expects a bare `/socket.io/` path. `ws: true` is what
          // actually lets the Upgrade: websocket handshake through (without
          // this entry the upgrade dies with the connection closing before
          // establishment, which is the console error this fixes).
          '^/[^/]+/socket\\.io/': {
            target: 'http://crm.localhost:9000',
            ws: true,
            changeOrigin: true,
            rewrite: (p) => p.replace(/^\/[^/]+(?=\/socket\.io\/)/, ''),
          },
          '^/(desk|app|login|api|assets|files|private)': {
            target: CRM_LOCAL_TARGET,
            ws: true,
            changeOrigin: true,
            // Always send requests to the volteo-local stack's nginx,
            // ignoring frappeProxy's default router (which builds the
            // upstream target from the *browser's* Host header, i.e.
            // "localhost:8081" — wrong site, wrong port).
            router: () => CRM_LOCAL_TARGET,
            headers: { Host: 'crm.localhost' },
          },
        },
      },
      optimizeDeps: {
        // Works around the pre-existing dep-scanner crash described above.
        exclude: ['frappe-ui'],
      },
    }),
  })

  return config
}
