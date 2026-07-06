package handler

import (
	"bytes"
	"net/http"
	"webserver/internal/config"
)

// 1. Faqat umumiy masalalar ro'yxati sahifasi (/problems)
func (a *App) GetProblems(w http.ResponseWriter, r *http.Request) {
	// Aniq /problems bo'lishi shart, noto'g'ri URL kelishini oldini olamiz
	if r.URL.Path != "/problems" {
		http.NotFound(w, r)
		return
	}

	if cached, err := a.Cache.GetString("page_problems_list"); err == nil {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		w.Write([]byte(cached))
		return
	}

	tmpl, exists := config.GetTemplate("pages/problems/problems")
	if !exists {
		http.Error(w, "Masalalar ro'yxati shabloni topilmadi", http.StatusInternalServerError)
		return
	}

	seoData := config.SEOContext{
		Title:       "Algoritmik Masalalar To'plami - CFM Contest",
		Description: "Dasturlash va matematika bo'yicha darajalangan mukammal masalalar.",
		URL:         "https://cfm.uz",
		H1Title:     "Olimpiada Masalalari",
	}

	var buf bytes.Buffer
	if err := tmpl.Execute(&buf, seoData); err != nil {
		http.Error(w, "Shablonni generatsiya qilishda xatolik", http.StatusInternalServerError)
		return
	}

	// DIQQAT: Agar SetString faqat 2 ta argument olsa, 300 ni olib tashlang.
	// Agar 3 ta argument olsa, pastdagi GetProblemDetail funksiyasiga ham vaqt qo'shing.
	_ = a.Cache.SetString("page_problems_list", buf.String())

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Write(buf.Bytes())
}

// 2. Dinamik individual masala sahifasi (/problem/{slug})
func (a *App) GetProblemDetail(w http.ResponseWriter, r *http.Request) {
	// Agar shablon bitta bo'lsa, kesh kaliti ham bitta bo'ladi
	cacheKey := "page_problem_detail_template"
	if cached, err := a.Cache.GetString(cacheKey); err == nil {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		w.Write([]byte(cached))
		return
	}

	tmpl, exists := config.GetTemplate("pages/problems/problem-detail")
	if !exists {
		http.Error(w, "Masala tafsiloti shabloni topilmadi", http.StatusInternalServerError)
		return
	}

	seoData := config.SEOContext{
		Title:       "Masala Sharti va Yechimi - CFM Contest",
		Description: "Masalaning kirish-chiqish formatlari, cheklovlari va testlari.",
		URL:         "https://cfm.uz",
		H1Title:     "Masala Tafsiloti",
	}

	var buf bytes.Buffer
	if err := tmpl.Execute(&buf, seoData); err != nil {
		http.Error(w, "Shablonni generatsiya qilishda xatolik", http.StatusInternalServerError)
		return
	}

	_ = a.Cache.SetString(cacheKey, buf.String())

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Write(buf.Bytes())
}
