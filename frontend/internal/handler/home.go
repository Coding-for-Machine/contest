package handler

import (
	"log"
	"net/http"
	"webserver/internal/cache"
	"webserver/internal/config"
)

// HomeHandler - Keshni qabul qiluvchi struktura
type HomeHandler struct {
	Cache *cache.Cache
}

// NewHomeHandler - Yangi handler yaratuvchi konstruktor
func NewHomeHandler(c *cache.Cache) *HomeHandler {
	return &HomeHandler{Cache: c}
}

func (h *HomeHandler) Home(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/" {
		NotFound(w, r)
		return
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")

	// 1. SEO va tezlik uchun: Tayyor render bo'lgan sahifa keshda bormi?
	cacheKey := "html:index"
	if cachedHTML, err := h.Cache.Memory.Get(cacheKey); err == nil {
		w.Header().Set("X-Cache", "HIT") // Keshdan chaqmoqdek tez berildi
		w.Write(cachedHTML)
		return
	}

	// 2. Keshda yo'q bo'lsa (CACHE MISS) - Birinchi marta render qilamiz
	w.Header().Set("X-Cache", "MISS")

	seo := config.SEOContext{
		Title:       "CFM Platformasi - Algoritmik Hakam Tizimi",
		Description: "Dasturlash masalalari va onlayn musobaqalar jamlangan eng tezkor o'zbek hakam tizimi.",
		URL:         "https://yourdomain.com" + r.URL.Path,
		H1Title:     "Dasturlashni CFM bilan o'rganing",
		// Data: backendData, // Agar DB yoki Backenddan keladigan ma'lumot bo'lsa shu yerga qo'yiladi
	}

	// HTML-ni to'g'ridan-to'g'ri brauzerga emas, vaqtincha xotira buferiga yozamiz
	// Bu keshga saqlab qo'yishimiz uchun kerak
	var buf []byte
	wBuffer := &bytesWriter{w: w, buf: &buf}

	// Layoutsiz index shablonini render qilamiz
	err := config.Templates["index"].Execute(wBuffer, seo)
	if err != nil {
		log.Printf("❌ Shablon render xatosi: %v", err)
		http.Error(w, "Ichki server xatoligi", http.StatusInternalServerError)
		return
	}

	// 3. Kelajakda keladigan SEO botlari va foydalanuvchilar uchun keshga yozib qo'yamiz
	// Sahifa endi 2-safardan boshlab DB'ga ham, shablon renderiga ham kirmaydi, tayyor HTML qaytadi
	_ = h.Cache.Memory.Set(cacheKey, buf)
}

// HTML-ni keshga ushlab qolish uchun yordamchi tuzilma
type bytesWriter struct {
	w   http.ResponseWriter
	buf *[]byte
}

func (bw *bytesWriter) Header() http.Header { return bw.w.Header() }
func (bw *bytesWriter) Write(b []byte) (int, error) {
	*bw.buf = append(*bw.buf, b...) // Kesh uchun saqlaydi
	return bw.w.Write(b)            // Brauzerga yuboradi
}
func (bw *bytesWriter) WriteHeader(statusCode int) { bw.w.WriteHeader(statusCode) }
