package handler

import (
	"bytes"
	"net/http"
	"strings"
	"webserver/internal/config"
)

// Gettests - Faqat barcha akademik testlar ro'yxatini chiqaradi (/tests)
func (a *App) Gettests(w http.ResponseWriter, r *http.Request) {
	// 🛠️ XAVFSIZLIK: /tests/ ko'rinishidagi noto'g'ri so'rovlarni 404 ga otish
	if r.URL.Path != "/tests" {
		http.NotFound(w, r)
		return
	}

	// BigCache xotirasidan tayyor keshni tekshirish
	if cached, err := a.Cache.GetString("page_tests_list"); err == nil {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		w.Write([]byte(cached))
		return
	}

	// Skaner tomonidan templates/pages/tests/tests.html uchun yasalgan kalit
	tmpl, exists := config.GetTemplate("pages/tests/tests")
	if !exists {
		http.Error(w, "Testlar bosh sahifa shabloni (pages/tests/tests) topilmadi", http.StatusInternalServerError)
		return
	}

	seoData := config.SEOContext{
		Title:       "Onlayn Imtihonlar va Sertifikatlash Testlari | CfM Contest",
		Description: "Matematika, informatika va dasturlash fanlaridan darajalangan testlar hamda rasmiy sertifikatlash imtihonlari.",
		URL:         "https://cfmcontest.uz",
		H1Title:     "Sertifikatlash Testlari",
	}

	var buf bytes.Buffer
	_ = tmpl.Execute(&buf, seoData)
	_ = a.Cache.SetString("page_tests_list", buf.String())

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Write(buf.Bytes())
}

// GetTestDetail - Faqat individual test haqida batafsil ma'lumot sahifasini ochadi (/test/...)
func (a *App) GetTestDetail(w http.ResponseWriter, r *http.Request) {
	// URL-dan slug-ni ajratib olish (Masalan: /test/python-asoslari -> python-asoslari)
	slug := strings.TrimPrefix(r.URL.Path, "/test/")
	if slug == "" {
		http.Redirect(w, r, "/tests", http.StatusSeeOther)
		return
	}

	// Skaner tomonidan templates/pages/tests/test-detail.html uchun yasalgan kalit
	tmpl, exists := config.GetTemplate("pages/tests/test-detail")
	if !exists {
		http.Error(w, "Test batafsil sahifa shabloni (pages/tests/test-detail) topilmadi", http.StatusNotFound)
		return
	}

	// URL'dagi chiziqchali matnni chiroyli sarlavhaga aylantirish (python-asoslari -> Python Asoslari)
	testTitle := config.SlugToTitle(slug)

	seoData := config.SEOContext{
		Title:       testTitle + " Testini Topshirish - CFM Contest",
		Description: testTitle + " onlayn testi savollar soni, qoidalari va berilgan vaqt me'yori.",
		URL:         "https://cfmcontest.uz" + slug,
		H1Title:     testTitle,
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	_ = tmpl.Execute(w, seoData)
}

// GetTestExam - Jonli imtihon topshirish sahifasi (/test/exam)
func (a *App) GetTestExam(w http.ResponseWriter, r *http.Request) {
	tmpl, exists := config.GetTemplate("pages/tests/exam")
	if !exists {
		http.Error(w, "Jonli imtihon shabloni (pages/tests/exam) topilmadi", http.StatusInternalServerError)
		return
	}

	// Tizimga kirgan foydalanuvchi seansini localStorage orqali JS o'qiydi,
	// Backend esa Google botlari uchun mukammal SEO tayyorlab beradi.
	seoData := config.SEOContext{
		Title:       "Jonli Imtihon Oynasi | CfM Contest",
		Description: "CfM Contest onlayn imtihon tizimi. Vaqt tugaguncha berilgan savollarga to'g'ri javob bering.",
		URL:         "https://cfmcontest.uz",
		H1Title:     "Onlayn Imtihon Davom Etmoqda",
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	_ = tmpl.Execute(w, seoData)
}

// GetTestResult - Imtihon yakuniy natijalari sahifasi (/test/result)
func (a *App) GetTestResult(w http.ResponseWriter, r *http.Request) {
	tmpl, exists := config.GetTemplate("pages/tests/result")
	if !exists {
		http.Error(w, "Natijalar shabloni (pages/tests/result) topilmadi", http.StatusInternalServerError)
		return
	}

	seoData := config.SEOContext{
		Title:       "Imtihon Natijasi va Ballar | CfM Contest",
		Description: "CfM Contest imtihon natijalari balni hisoblash, xatolar tahlili va elektron sertifikat olish oynasi.",
		URL:         "https://cfmcontest.uz",
		H1Title:     "Sizning Imtihon Natijangiz",
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	_ = tmpl.Execute(w, seoData)
}
