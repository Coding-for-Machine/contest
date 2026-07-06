package handler

import (
	"bytes"
	"net/http"
	"strings"
	"webserver/internal/config"
)

func (a *App) GetContests(w http.ResponseWriter, r *http.Request) {
	// Musobaqa ichidagi masala sahifasi (/contest/olimpiada/problem/A)
	if strings.Contains(r.URL.Path, "/problem/") {
		a.getContestProblem(w, r)
		return
	}

	// Alohida musobaqa sahifasi (/contest/olimpiada)
	if strings.HasPrefix(r.URL.Path, "/contest/") {
		slug := strings.TrimPrefix(r.URL.Path, "/contest/")
		if slug == "" {
			http.Redirect(w, r, "/contests", http.StatusSeeOther)
			return
		}
		a.getContestDetail(w, r, slug)
		return
	}

	// Umumiy ro'yxat (/contests)
	if cached, err := a.Cache.GetString("page_contests_list"); err == nil {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		w.Write([]byte(cached))
		return
	}

	tmpl, exists := config.GetTemplate("pages/contests/contests")
	if !exists {
		http.Error(w, "Musobaqalar ro'yxati shabloni topilmadi", http.StatusInternalServerError)
		return
	}

	seoData := config.SEOContext{
		Title:       "Onlayn Dasturlash Musobaqalari - CFM Contest",
		Description: "Algoritmik va matematik jonli olimpiadalar. Qatnashing va reytingingizni oshiring.",
		URL:         "https://cfm.uz",
		H1Title:     "Jonli va Kutilayotgan Musobaqalar",
	}

	var buf bytes.Buffer
	_ = tmpl.Execute(&buf, seoData)
	_ = a.Cache.SetString("page_contests_list", buf.String())

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Write(buf.Bytes())
}

func (a *App) getContestDetail(w http.ResponseWriter, r *http.Request, slug string) {
	cacheKey := "page_contest_detail_" + slug
	if cached, err := a.Cache.GetString(cacheKey); err == nil {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		w.Write([]byte(cached))
		return
	}

	tmpl, exists := config.GetTemplate("pages/contests/contest-detail")
	if !exists {
		http.NotFound(w, r)
		return
	}

	contestTitle := config.SlugToTitle(slug)
	seoData := config.SEOContext{
		Title:       contestTitle + " - Musobaqa Masalalari",
		Description: contestTitle + " musobaqasining jonli monitoringi va vaqt cheklovlari.",
		URL:         "https://cfm.uz" + slug,
		H1Title:     contestTitle,
	}

	var buf bytes.Buffer
	_ = tmpl.Execute(&buf, seoData)
	_ = a.Cache.SetString(cacheKey, buf.String())

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Write(buf.Bytes())
}

func (a *App) getContestProblem(w http.ResponseWriter, r *http.Request) {
	pathParts := strings.Split(strings.Trim(r.URL.Path, "/"), "/")
	if len(pathParts) < 4 {
		http.NotFound(w, r)
		return
	}

	contestSlug := pathParts[1]
	problemLetter := pathParts[3]
	cacheKey := "page_contest_" + contestSlug + "_prob_" + problemLetter

	if cached, err := a.Cache.GetString(cacheKey); err == nil {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		w.Write([]byte(cached))
		return
	}

	tmpl, exists := config.GetTemplate("pages/contests/contest-problem")
	if !exists {
		http.Error(w, "Musobaqa masala shabloni topilmadi", http.StatusInternalServerError)
		return
	}

	contestTitle := config.SlugToTitle(contestSlug)
	seoData := config.SEOContext{
		Title:       "Masala " + strings.ToUpper(problemLetter) + " | " + contestTitle + " - CFM",
		Description: contestTitle + " musobaqasidagi " + strings.ToUpper(problemLetter) + "-masala sharti.",
		URL:         "https://cfm.uz" + r.URL.Path,
		H1Title:     "Masala " + strings.ToUpper(problemLetter),
	}

	var buf bytes.Buffer
	_ = tmpl.Execute(&buf, seoData)
	_ = a.Cache.SetString(cacheKey, buf.String())

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Write(buf.Bytes())
}
