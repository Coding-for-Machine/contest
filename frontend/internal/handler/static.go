package handler

import (
	"log"
	"net/http"
	"webserver/internal/config"
)

// Login - Tizimga kirish sahifasi
func Login(w http.ResponseWriter, r *http.Request) {
	// Sarlavha har doim Execute funksiyasidan tepada bo'lishi kerak
	w.Header().Set("Content-Type", "text/html; charset=utf-8")

	seo := config.SEOContext{
		Title:       "Tizimga kirish - CFM Contest",
		Description: "CFM algoritm platformasidagi profilingizga kiring.",
		URL:         "https://yourdomain.com",
		H1Title:     "Xush kelibsiz",
	}

	err := config.Templates["login"].Execute(w, seo)
	if err != nil {
		log.Printf("❌ Login shablon xatosi: %v", err)
		http.Error(w, "Sahifa yuklanishida xatolik", http.StatusInternalServerError)
	}
}

// NotFound - 404 Xatolik sahifasi (TUZATILGAN QISM)
func NotFound(w http.ResponseWriter, r *http.Request) {
	// QADAM 1: Birinchi bo'lib ma'lumot turi HTML ekanligini e'lon qilamiz
	w.Header().Set("Content-Type", "text/html; charset=utf-8")

	// QADAM 2: Keyin HTTP status kodini yuboramiz
	w.WriteHeader(http.StatusNotFound)

	seo := config.SEOContext{
		Title:       "Sahifa topilmadi - 404",
		Description: "Afsuski, siz qidirayotgan sahifa platformamizda mavjud emas.",
		H1Title:     "Ushbu sahifa mavjud emas",
	}

	tmpl, exists := config.Templates["pages/404"]
	if !exists {
		http.Error(w, "404 Sahifa topilmadi", http.StatusNotFound)
		return
	}

	// QADAM 3: Eng oxirida shablonni render qilamiz
	_ = tmpl.Execute(w, seo)
}
