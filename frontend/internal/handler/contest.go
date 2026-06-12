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

type ContestHandler struct {
	Cache *cache.Cache
}

func NewContestHandler(c *cache.Cache) *ContestHandler {
	return &ContestHandler{Cache: c}
}

func (h *ContestHandler) GetContests(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")

	slug := strings.TrimPrefix(r.URL.Path, "/contests/")
	slug = strings.TrimSpace(slug)

	var cacheKey string
	var templateName string
	var apiURL string
	var title string

	if slug == "" || slug == "contests" {
		cacheKey = "html:contests_list"
		templateName = "pages/contests"
		apiURL = config.BackendBaseURL + "/contests"
		title = "Onlayn Dasturlash Musobaqalari - CFM"
	} else {
		cacheKey = fmt.Sprintf("html:contest:%s", slug)
		templateName = "pages/contest-detail"
		apiURL = fmt.Sprintf("%s/contests/%s", config.BackendBaseURL, slug)
		title = config.SlugToTitle(slug) + " - CFM Musobaqa"
	}

	if cachedHTML, err := h.Cache.Memory.Get(cacheKey); err == nil {
		w.Header().Set("X-Cache", "HIT")
		w.Write(cachedHTML)
		return
	}

	w.Header().Set("X-Cache", "MISS")

	resp, err := http.Get(apiURL)
	var backendData interface{}
	if err == nil && resp.StatusCode == http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		_ = json.Unmarshal(body, &backendData)
		resp.Body.Close()
	}

	seo := config.SEOContext{
		Title:       title,
		Description: "CFM onlayn algoritmlar musobaqasida qatnashing va o'z darajangizni tekshiring.",
		URL:         "https://yourdomain.com" + r.URL.Path,
		H1Title:     title,
		Data:        backendData,
	}

	tmpl, exists := config.Templates[templateName]
	if !exists {
		NotFound(w, r)
		return
	}

	var buf []byte
	wBuffer := &bytesWriter{w: w, buf: &buf}

	err = tmpl.Execute(wBuffer, seo)
	if err != nil {
		log.Printf("❌ Contests shablon xatosi: %v", err)
		http.Error(w, "Ichki server xatoligi", http.StatusInternalServerError)
		return
	}

	_ = h.Cache.Memory.Set(cacheKey, buf)
}
