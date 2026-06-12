package config

import (
	"log"
	"path/filepath"
	"strings"
	"text/template" // 🛠️ FIKS: html/template o'rniga text/template ishlatiladi
)

type SEOContext struct {
	Title       string
	Description string
	URL         string
	H1Title     string
	Data        interface{}
}

// Global shablonlar xaritasi (Endi text/template turi bilan)
var Templates = make(map[string]*template.Template)

const BackendBaseURL = "http://localhost:3000/api"

// LoadTemplates - Shablonlarni har birini alohida (Layoutsiz) yuklash
func LoadTemplates(wd string) {
	// 1. index.html sahifasini alohida yuklash
	indexPath := filepath.Join(wd, "templates", "index.html")
	tmplIndex, err := template.ParseFiles(indexPath)
	if err != nil {
		log.Printf("❌ Xatolik: index.html yuklanmadi: %v", err)
	} else {
		Templates["index"] = tmplIndex
		log.Println("✅ index.html muvaffaqiyatli yuklandi (Layoutsiz)")
	}

	// 2. login.html sahifasini alohida yuklash
	loginPath := filepath.Join(wd, "templates", "login.html")
	tmplLogin, err := template.ParseFiles(loginPath)
	if err != nil {
		log.Printf("❌ Xatolik: login.html yuklanmadi: %v", err)
	} else {
		Templates["login"] = tmplLogin
		log.Println("✅ login.html muvaffaqiyatli yuklandi (Layoutsiz)")
	}

	// 3. Ichki sahifalarni (pages/*.html) avtomat yuklash
	pages, err := filepath.Glob(filepath.Join(wd, "templates", "pages", "*.html"))
	if err != nil {
		log.Printf("❌ Xatolik: Pages papkasini o'qishda xato: %v", err)
		return
	}

	for _, page := range pages {
		name := strings.TrimSuffix(filepath.Base(page), ".html")

		tmpl, err := template.ParseFiles(page)
		if err != nil {
			log.Printf("❌ Xatolik: [%s.html] shablonida sintaksis xato bor: %v", name, err)
			continue
		}
		Templates["pages/"+name] = tmpl
		log.Printf("✅ pages/%s.html muvaffaqiyatli yuklandi (Layoutsiz)", name)
	}
}

func SlugToTitle(slug string) string {
	words := strings.Split(slug, "-")
	for i, word := range words {
		if len(word) > 0 {
			words[i] = strings.ToUpper(word[:1]) + word[1:]
		}
	}
	return strings.Join(words, " ")
}
