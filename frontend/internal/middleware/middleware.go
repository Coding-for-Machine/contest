package middleware

import (
	"compress/gzip"
	"io"
	"net/http"
	"path/filepath"
	"strings"
)

type gzipResponseWriter struct {
	io.Writer
	http.ResponseWriter
}

func (w gzipResponseWriter) Write(b []byte) (int, error) {
	return w.Writer.Write(b)
}

// GlobalMiddleware - Tezlik, Xavfsizlik va Keshni boshqaruvchi asosiy zanjir
func GlobalMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		path := r.URL.Path
		ext := filepath.Ext(path)

		// 1. Maxfiy fayllarni himoya qilish
		if ext == ".go" || ext == ".pem" || ext == ".mod" || ext == ".sum" {
			w.WriteHeader(http.StatusForbidden)
			w.Write([]byte("403 Forbidden - Ruxsat berilmagan!"))
			return
		}

		// 2. HTTP/2 Server Push (Faqat sahifalar ochilganda asosiy assetlarni yuborish)
		if ext == "" && !strings.HasPrefix(path, "/assets/") {
			if pusher, ok := w.(http.Pusher); ok {
				pushOpts := &http.PushOptions{Header: http.Header{"Accept-Encoding": r.Header["Accept-Encoding"]}}
				_ = pusher.Push("/assets/css/style.css", pushOpts)
				_ = pusher.Push("/assets/js/main.js", pushOpts)
			}
		}

		// 3. Xavfsizlik Headerlari
		w.Header().Set("X-Content-Type-Options", "nosniff")
		w.Header().Set("X-Frame-Options", "DENY")
		w.Header().Set("X-XSS-Protection", "1; mode=block")
		w.Header().Set("Referrer-Policy", "strict-origin-when-cross-origin")

		// 4. Kesh boshqaruvi
		if strings.HasPrefix(path, "/assets/") {
			w.Header().Set("Cache-Control", "public, max-age=31536000, immutable")
		} else {
			w.Header().Set("Cache-Control", "no-cache, no-store, must-revalidate")
		}

		// 5. Gzip Siqish
		if strings.Contains(r.Header.Get("Accept-Encoding"), "gzip") &&
			(ext == ".html" || ext == ".css" || ext == ".js" || ext == "") {
			w.Header().Set("Content-Encoding", "gzip")
			gz := gzip.NewWriter(w)
			defer gz.Close()
			w = gzipResponseWriter{Writer: gz, ResponseWriter: w}
		}

		// MIME turlarini aniqlashtirish
		switch ext {
		case ".css":
			w.Header().Set("Content-Type", "text/css; charset=utf-8")
		case ".js":
			w.Header().Set("Content-Type", "application/javascript; charset=utf-8")
		}

		next.ServeHTTP(w, r)
	})
}
