import { io } from 'socket.io-client'
import { getCachedListResource, getCachedResource } from 'frappe-ui'

export function initSocket() {
  let host = window.location.hostname
  let siteName = window.site_name
  // In the Vite dev server (port set, e.g. :8081) connect to the page's own
  // origin so the socket goes through the dev proxy (which forwards
  // `/socket.io/` upstream with `ws: true`). Going straight to
  // `host:socketio_port` from the browser bypasses the proxy and the
  // websocket upgrade dies before establishment. In production there is no
  // port on the page URL, so we keep the original same-origin behaviour
  // (no port, page protocol).
  let isDevServer = !!window.location.port
  let url = isDevServer
    ? `${window.location.origin}/${siteName}`
    : `${window.location.protocol}//${host}/${siteName}`

  let socket = io(url, {
    withCredentials: true,
    reconnectionAttempts: 5,
  })
  socket.on('refetch_resource', (data) => {
    if (data.cache_key) {
      let resource =
        getCachedResource(data.cache_key) ||
        getCachedListResource(data.cache_key)
      if (resource) {
        resource.reload()
      }
    }
  })
  return socket
}
