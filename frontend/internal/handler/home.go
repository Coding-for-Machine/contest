package handler

import (
	"bytes"
	"net/http"
	"webserver/internal/config"
)

func (a *App) Home(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/" {
		http.NotFound(w, r)
		return
	}

	// appCache o'rniga a.Cache orqali BigCache chaqiriladi
	if cached, err := a.Cache.GetString("page_home"); err == nil {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		w.Write([]byte(cached))
		return
	}

	tmpl, exists := config.GetTemplate("index")
	if !exists {
		http.Error(w, "Bosh sahifa shabloni topilmadi", http.StatusInternalServerError)
		return
	}

	seoData := config.SEOContext{
		Title:       "CFM Contest - Algoritmik Masalalar, Kurslar va Olimpiyada platforma",
		Description: "Dasturlashni va matematika noldan professional darajagacha o'rganing.",
		URL:         "https://cfm.uz",
		H1Title:     "CFM Innovatsion Ta'lim Platformasi",
	}

	var buf bytes.Buffer
	_ = tmpl.Execute(&buf, seoData)
	_ = a.Cache.SetString("page_home", buf.String())

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Write(buf.Bytes())
}
