package handler

import (
	"net/http"
	"webserver/internal/config"
)

// GetStaticPage - /help yoki /settings kabi statik sahifalarni yuklaydi
func (a *App) GetStaticPage(w http.ResponseWriter, r *http.Request, pageKey string) {
	tmpl, exists := config.GetTemplate(pageKey)
	if !exists {
		http.NotFound(w, r)
		return
	}

	seoData := config.SEOContext{
		Title:       "Yordam va Yo'riqnoma - CFM",
		Description: "CFM platformasidan foydalanish bo'yicha tez-tez beriladigan savollar.",
		URL:         "https://cfm.uz" + r.URL.Path,
		H1Title:     "Platforma qo'llanmasi",
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	_ = tmpl.Execute(w, seoData)
}
