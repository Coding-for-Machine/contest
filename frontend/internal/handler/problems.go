package handler

import (
	"bytes" // bytesWriter o'rniga standart bytes.Buffer ishlatish tavsiya etiladi
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"strings"
	"webserver/internal/cache"
	"webserver/internal/config"
)

type ProblemsHandler struct {
	Cache *cache.Cache
}

func NewProblemsHandler(c *cache.Cache) *ProblemsHandler {
	return &ProblemsHandler{Cache: c}
}

// GetProblems - Ham ro'yxatni, ham dinamik sluglarni bitta joyda xavfsiz boshqaradi
func (h *ProblemsHandler) GetProblems(w http.ResponseWriter, r *http.Request) {
	slug := strings.TrimPrefix(r.URL.Path, "/problems/")
	slug = strings.TrimSpace(slug)
	slug = strings.TrimSuffix(slug, "/")

	var cacheKey string
	var templateName string
	var apiURL string
	var title string

	if slug == "" || r.URL.Path == "/problems" {
		cacheKey = "html:problems_list"
		templateName = "pages/problems"
		apiURL = config.BackendBaseURL + "/problems"
		title = "Barcha Dasturlash Masalalari - CFM"
	} else {
		if strings.Contains(slug, "/") {
			NotFound(w, r)
			return
		}
		cacheKey = fmt.Sprintf("html:problem:%s", slug)
		templateName = "pages/problem-detail"
		apiURL = fmt.Sprintf("%s/problems/%s", config.BackendBaseURL, slug)
		title = config.SlugToTitle(slug) + " - CFM Masala"
	}

	// QADAM 1: Keshni tekshirish
	if cachedHTML, err := h.Cache.Memory.Get(cacheKey); err == nil {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		w.Header().Set("X-Cache", "HIT")
		w.Write(cachedHTML)
		return
	}

	// QADAM 2: Backend API dan ma'lumotni yuklash (Xato bo'lsa ham sahifa o'lmaydi)
	var backendData interface{}
	resp, err := http.Get(apiURL)

	if err == nil && resp.StatusCode == http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		_ = json.Unmarshal(body, &backendData)
		resp.Body.Close()
	} else {
		// Backend o'chiq bo'lsa konsolga ogohlantirish yozadi, lekin sayt ishlayveradi
		log.Printf("⚠️ Backend API bilan aloqa yo'q yoki xato (%s). Sahifa bo'sh ma'lumot bilan render bo'lmoqda.", apiURL)
		if resp != nil {
			resp.Body.Close()
		}
	}

	seo := config.SEOContext{
		Title:       title,
		Description: "Dasturlash bilimingizni CFM algoritmik masalalari bilan oshiring.",
		URL:         "https://yourdomain.com" + r.URL.Path,
		H1Title:     title,
		Data:        backendData, // Agar backend ishlamasa, bu ichi bo'sh (nil) ketadi
	}

	// QADAM 3: Shablon borligini tekshirish
	tmpl, exists := config.Templates[templateName]
	if !exists {
		log.Printf("❌ %s shabloni yuklangan shablonlar ichidan topilmadi!", templateName)
		NotFound(w, r)
		return
	}

	// HTML-ni keshga xavfsiz olish uchun buffer
	var buf bytes.Buffer

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Header().Set("X-Cache", "MISS")

	// Shablonda xato bo'lsa brauzer oq sahifa ko'rsatmasligi uchun avval bufferga render qilamiz
	err = tmpl.Execute(&buf, seo)
	if err != nil {
		log.Printf("❌ Problems shablon xatosi: %v", err)
		http.Error(w, "Ichki server xatoligi", http.StatusInternalServerError)
		return
	}

	// Bufferni brauzerga yuboramiz
	_, _ = w.Write(buf.Bytes())

	// QADAM 4: Kelajakda keladigan so'rovlar uchun keshga yozish
	_ = h.Cache.Memory.Set(cacheKey, buf.Bytes())
}
