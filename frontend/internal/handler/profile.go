package handler

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"strings"
	"webserver/internal/cache"
	"webserver/internal/config"
)

type ProfileHandler struct {
	Cache *cache.Cache
}

func NewProfileHandler(c *cache.Cache) *ProfileHandler {
	return &ProfileHandler{Cache: c}
}

func (h *ProfileHandler) GetProfile(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")

	// URL'dan username'ni ajratib olamiz (/u/asadbek -> asadbek)
	username := strings.TrimPrefix(r.URL.Path, "/u/")
	username = strings.TrimSpace(username)

	// Agar shunchaki /u/ deb kirsa, 404 beramiz
	if username == "" {
		NotFound(w, r)
		return
	}

	// Har bir foydalanuvchi uchun unikal kesh kaliti
	cacheKey := fmt.Sprintf("html:profile:%s", username)

	// 1. Keshni tekshiramiz
	if cachedHTML, err := h.Cache.Memory.Get(cacheKey); err == nil {
		w.Header().Set("X-Cache", "HIT")
		w.Write(cachedHTML)
		return
	}

	w.Header().Set("X-Cache", "MISS")

	// 2. Backend API'dan user ma'lumotlarini yuklaymiz
	apiURL := fmt.Sprintf("%s/users/%s", config.BackendBaseURL, username)
	resp, err := http.Get(apiURL)
	var backendData interface{}
	if err == nil && resp.StatusCode == http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		_ = json.Unmarshal(body, &backendData)
		resp.Body.Close()
	}

	seo := config.SEOContext{
		Title:       username + " (Foydalanuvchi profili) - CFM Contest",
		Description: username + " profiling dasturlash ko'rsatkichlari, reytingi va yechgan masalalari.",
		URL:         "https://yourdomain.com" + r.URL.Path,
		H1Title:     "Foydalanuvchi: " + username,
		Data:        backendData,
	}

	tmpl, exists := config.Templates["pages/profile"]
	if !exists {
		NotFound(w, r)
		return
	}

	var buf []byte
	wBuffer := &bytesWriter{w: w, buf: &buf}

	err = tmpl.Execute(wBuffer, seo)
	if err != nil {
		log.Printf("❌ Profile shablon xatosi: %v", err)
		http.Error(w, "Ichki server xatoligi", http.StatusInternalServerError)
		return
	}

	// 3. Keshga yozib qo'yamiz
	_ = h.Cache.Memory.Set(cacheKey, buf)
}
