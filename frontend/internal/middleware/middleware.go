package middleware

import (
	"compress/gzip"
	"io"
	"net/http"
	"path/filepath"
	"strings"
)

// gzipResponseWriter - Response va Writer-ni xavfsiz bog'lovchi struktura
type gzipResponseWriter struct {
	io.Writer
	http.ResponseWriter
}

func (w gzipResponseWriter) Header() http.Header {
	return w.ResponseWriter.Header()
}

func (w gzipResponseWriter) WriteHeader(statusCode int) {
	w.ResponseWriter.WriteHeader(statusCode)
}

func (w gzipResponseWriter) Write(b []byte) (int, error) {
	if w.ResponseWriter.Header().Get("Content-Type") == "" {
		w.ResponseWriter.Header().Set("Content-Type", http.DetectContentType(b))
	}
	return w.Writer.Write(b)
}

// GlobalMiddleware - Saytni to'liq himoya qiluvchi va barcha kerakli statik fayllarga ruxsat beruvchi zanjir
func GlobalMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		path := strings.ToLower(r.URL.Path)
		ext := filepath.Ext(path)

		// =================================================================
		// 1. QAT'IY BLOKLASH (BLACK-LIST) VA PAPKA HIMOYaSI
		// =================================================================
		// Kod fayllari, maxfiy kalitlar va ichki tizim papkalariga kirish mutloq taqiqlanadi
		if ext == ".go" || ext == ".pem" || ext == ".mod" || ext == ".sum" || ext == ".env" || ext == ".json" || ext == ".html" ||
			strings.Contains(path, "/internal/") ||
			strings.Contains(path, "/cfm/") ||
			strings.Contains(path, "/roba/") {

			w.WriteHeader(http.StatusForbidden)
			w.Write([]byte("403 Forbidden - Bu resurs maxfiy va ruxsat berilmagan!"))
			return
		}

		// =================================================================
		// 2. FAQAT RUXSAT BERILGAN YO'NALIShLAR (WHITE-LIST & STATIC SAFE)
		// =================================================================
		isSEOFile := (path == "/robots.txt" || path == "/sitemap.xml")
		isStaticAsset := strings.HasPrefix(path, "/assets/") || strings.HasPrefix(path, "/static/")
		isHTMLPage := (ext == "") // Dinamik HTML render qilinadigan sahifalar (URL manzillar)

		if !isSEOFile && !isStaticAsset && !isHTMLPage {
			w.WriteHeader(http.StatusNotFound)
			w.Write([]byte("404 Not Found - Resurs topilmadi!"))
			return
		}

		// =================================================================
		// 3. HTTP/2 SERVER PUSH (Faqat HTML sahifalarda tezlikni oshirish uchun)
		// =================================================================
		if r.Method == http.MethodGet && isHTMLPage {
			if pusher, ok := w.(http.Pusher); ok {
				pushOpts := &http.PushOptions{
					Header: http.Header{"Accept-Encoding": r.Header["Accept-Encoding"]},
				}
				// Ildiz manzildan to'g'ri push qilish uchun havolalar fiks qilindi
				_ = pusher.Push("/assets/css/style.css", pushOpts)
				_ = pusher.Push("/assets/js/main.js", pushOpts)
			}
		}

		// =================================================================
		// 4. XAVFSIZLIK VA KESH HEADERLARI (SEO standartlari)
		// =================================================================
		w.Header().Set("X-Content-Type-Options", "nosniff")
		w.Header().Set("X-Frame-Options", "DENY")
		w.Header().Set("X-XSS-Protection", "1; mode=block")
		w.Header().Set("Referrer-Policy", "strict-origin-when-cross-origin")

		if isStaticAsset {
			// 🧠 AQLLI KESH: CSS, JS, Rasmlar (.png, .webp, .png) va Shriftlarni brauzerda 1 yilga saqlash
			w.Header().Set("Cache-Control", "public, max-age=31536000, immutable")
		} else {
			// Dinamik ma'lumotlar keshda qolib ketmasligi shart
			w.Header().Set("Cache-Control", "no-cache, no-store, must-revalidate")
		}

		// =================================================================
		// 5. GZIP SIQISH VA NAVBATDAGI HANDLERLARGA UZATISH
		// =================================================================
		// ⚠️ FIKS: Rasmlarni (.png, .jpg, .webp) gzip bilan qayta siqish CPU-ni bekorga charchatadi (chunki ular allaqachon siqilgan).
		// Shuning uchun faqat matnli statik fayllarni (css, js, xml, txt) va HTML sahifalarni siqamiz:
		isCompressible := ext == ".css" || ext == ".js" || ext == ".txt" || ext == ".xml" || isHTMLPage

		if strings.Contains(r.Header.Get("Accept-Encoding"), "gzip") && isCompressible {
			w.Header().Set("Content-Encoding", "gzip")
			gz := gzip.NewWriter(w)
			defer gz.Close()

			gzw := gzipResponseWriter{Writer: gz, ResponseWriter: w}
			next.ServeHTTP(gzw, r)
			return
		}

		next.ServeHTTP(w, r)
	})
}
