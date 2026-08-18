interface UploadOptions {
  fileObj?: File
  private?: boolean
  fileUrl?: string
  folder?: string
  doctype?: string
  docname?: string
  fieldname?: string
  type?: string
}

type EventListenerOption = 'start' | 'progress' | 'finish' | 'error'

declare global {
  interface Window {
    csrf_token?: string
  }
}

class FilesUploadHandler {
  listeners: { [event: string]: ((...args: unknown[]) => void)[] }
  failed: boolean

  constructor() {
    this.listeners = {}
    this.failed = false
  }

  on(event: EventListenerOption, handler: (...args: unknown[]) => void) {
    this.listeners[event] = this.listeners[event] || []
    this.listeners[event].push(handler)
  }

  trigger(event: string, data?: unknown) {
    const handlers = this.listeners[event] || []
    handlers.forEach((handler) => {
      handler.call(this, data)
    })
  }

  upload(file: File | null, options: UploadOptions): Promise<unknown> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      xhr.upload.addEventListener('loadstart', () => {
        this.trigger('start')
      })
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          this.trigger('progress', {
            uploaded: e.loaded,
            total: e.total,
          })
        }
      })
      xhr.upload.addEventListener('load', () => {
        this.trigger('finish')
      })
      xhr.addEventListener('error', () => {
        this.trigger('error')
        reject()
      })
      xhr.onreadystatechange = () => {
        if (xhr.readyState == XMLHttpRequest.DONE) {
          let error: unknown
          if (xhr.status === 200) {
            let r: unknown
            try {
              r = JSON.parse(xhr.responseText)
            } catch {
              r = xhr.responseText
            }
            const out = (r as { message?: unknown })?.message || r
            resolve(out)
          } else if (xhr.status === 403) {
            error = JSON.parse(xhr.responseText)
          } else if (xhr.status === 413) {
            this.failed = true
            error = 'Size exceeds the maximum allowed file size.'
          } else {
            this.failed = true
            try {
              error = JSON.parse(xhr.responseText)
            } catch {
              // pass
            }
          }
          if (error && (error as { exc?: string }).exc) {
            console.error(JSON.parse((error as { exc: string }).exc)[0])
          }
          reject(error)
        }
      }

      xhr.open('POST', '/api/method/upload_file', true)
      xhr.setRequestHeader('Accept', 'application/json')

      if (window.csrf_token && window.csrf_token !== '{{ csrf_token }}') {
        xhr.setRequestHeader('X-Frappe-CSRF-Token', window.csrf_token)
      }

      const formData = new FormData()

      if (options.fileObj && file?.name) {
        formData.append('file', options.fileObj, file.name)
      }
      // No public files, ever (owner decision) -- always upload private,
      // regardless of what the caller passes. The server enforces this too
      // (crm.permissions.file_privacy), this just avoids the round trip.
      formData.append('is_private', '1')
      formData.append('folder', options.folder || 'Home')

      if (options.fileUrl) {
        formData.append('file_url', options.fileUrl)
      }

      if (options.doctype) {
        formData.append('doctype', options.doctype)
      }

      if (options.docname) {
        formData.append('docname', options.docname)
      }

      if (options.fieldname) {
        formData.append('fieldname', options.fieldname)
      }

      if (options.type) {
        formData.append('type', options.type)
      }

      xhr.send(formData)
    })
  }
}

export default FilesUploadHandler
