package handler

import (
	"net/http"
	"strings"
	"webserver/internal/config"
)

func (a *App) GetProfile(w http.ResponseWriter, r *http.Request) {
	username := strings.TrimPrefix(r.URL.Path, "/u/")
	if username == "" {
		http.Redirect(w, r, "/", http.StatusSeeOther)
		return
	}

	tmpl, exists := config.GetTemplate("pages/users/profile")
	if !exists {
		http.Error(w, "Profil shabloni topilmadi", http.StatusInternalServerError)
		return
	}

	seoData := config.SEOContext{
		Title:       username + " (Shaxsiy Profil) - CFM Contest",
		Description: username + " foydalanuvchisining reytingi va CFM platformasidagi yutuqlari.",
		URL:         "https://cfm.uz" + username,
		H1Title:     "Foydalanuvchi kabineti",
		Data:        username,
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	_ = tmpl.Execute(w, seoData)
}
