package handler

import (
	"net/http"
	"webserver/internal/config"
)

// Newlogin - Mustaqil login funksiyasi (Seanslar aralashmasligi uchun odatda keshlanmaydi)
func Newlogin(w http.ResponseWriter, r *http.Request) {
	tmpl, exists := config.GetTemplate("login")
	if !exists {
		http.Error(w, "Login shabloni topilmadi", http.StatusInternalServerError)
		return
	}

	seoData := config.SEOContext{
		Title:       "Tizimga Kirish - CFM Contest",
		Description: "CFM platformasidagi shaxsiy profilingizga kiring va musobaqalarda qatnashing.",
		URL:         "https://cfm.uz",
		H1Title:     "Tizimga xavfsiz kirish",
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	_ = tmpl.Execute(w, seoData)
}
