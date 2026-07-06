package handler

import (
	"bytes"
	"net/http"
	"strings"
	"webserver/internal/config"
)

func (a *App) GetCourses(w http.ResponseWriter, r *http.Request) {
	if cached, err := a.Cache.GetString("page_courses_list"); err == nil {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		w.Write([]byte(cached))
		return
	}

	tmpl, exists := config.GetTemplate("pages/courses/courses")
	if !exists {
		http.Error(w, "Kurslar bosh sahifa shabloni topilmadi", http.StatusInternalServerError)
		return
	}

	seoData := config.SEOContext{
		Title:       "Professional Dasturlash va Matematika Kurslari - CFM Contest",
		Description: "Go, Python, Algoritmlar va Matematika yo'nalishida noldan professional darslar.",
		URL:         "https://cfm.uz",
		H1Title:     "Bizning Onlayn Kurslarimiz",
	}

	var buf bytes.Buffer
	_ = tmpl.Execute(&buf, seoData)
	_ = a.Cache.SetString("page_courses_list", buf.String())

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Write(buf.Bytes())
}

func (a *App) GetCourseDetail(w http.ResponseWriter, r *http.Request) {
	slug := strings.TrimPrefix(r.URL.Path, "/course/")
	if slug == "" {
		http.Redirect(w, r, "/courses", http.StatusSeeOther)
		return
	}

	cacheKey := "page_course_detail_" + slug
	if cached, err := a.Cache.GetString(cacheKey); err == nil {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		w.Write([]byte(cached))
		return
	}

	tmpl, exists := config.GetTemplate("pages/courses/course-detail")
	if !exists {
		http.NotFound(w, r)
		return
	}

	courseTitle := config.SlugToTitle(slug)
	seoData := config.SEOContext{
		Title:       courseTitle + " Kursi (Noldan Professionalgacha) - CFM",
		Description: courseTitle + " kursi darslar moduli va amaliy topshiriqlar rejasi.",
		URL:         "https://cfm.uz" + slug,
		H1Title:     courseTitle + " Kursi Dasturi",
	}

	var buf bytes.Buffer
	_ = tmpl.Execute(&buf, seoData)
	_ = a.Cache.SetString(cacheKey, buf.String())

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Write(buf.Bytes())
}

func (a *App) GetLessonDetail(w http.ResponseWriter, r *http.Request) {
	slug := strings.TrimPrefix(r.URL.Path, "/lesson/")
	if slug == "" {
		http.NotFound(w, r)
		return
	}

	tmpl, exists := config.GetTemplate("pages/courses/lesson")
	if !exists {
		http.NotFound(w, r)
		return
	}

	lessonTitle := config.SlugToTitle(slug)
	seoData := config.SEOContext{
		Title:       lessonTitle + " - Video Dars va Konspekt | CFM",
		Description: lessonTitle + " darsining amaliy videosi va qisqacha konspekti.",
		URL:         "https://cfm.uz" + slug,
		H1Title:     lessonTitle,
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	_ = tmpl.Execute(w, seoData)
}
