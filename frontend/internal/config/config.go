package config

import (
	"html/template"
	"log"
	"os"
	"path/filepath"
	"strings"
	"sync"
)

// SEOContext - Google va boshqa qidiruv botlari (SEO) uchun mukammal ma'lumot uzatish strukturasi
type SEOContext struct {
	Title       string      `json:"title"`
	Description string      `json:"description"`
	URL         string      `json:"url"`
	H1Title     string      `json:"h1_title"`
	Data        interface{} `json:"data"`
}

var (
	Templates   = make(map[string]*template.Template)
	templatesMu sync.RWMutex
)

func LoadTemplates(wd string) {
	templatesMu.Lock()
	defer templatesMu.Unlock()

	// Loyihangiz tuzilmasiga ko'ra asosiy templates papkasi manzili
	baseDir := filepath.Join(wd, "templates")

	err := filepath.Walk(baseDir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		// Faqat .html kengaytmali fayllarni olamiz
		if !info.IsDir() && strings.HasSuffix(info.Name(), ".html") {

			// Faylning nisbiy yo'lini aniqlaymiz (Masalan: templates/pages/tests/exam.html -> pages/tests/exam.html)
			relPath, err := filepath.Rel(baseDir, path)
			if err != nil {
				return err
			}

			// Kesh xaritasi (Map Key) uchun chiroyli nom yasaymiz (Masalan: pages/tests/exam)
			templateKey := strings.TrimSuffix(relPath, ".html")

			// HTML shablonini Parse qilamiz (Xavfsiz html/template paketi orqali)
			tmpl, err := template.ParseFiles(path)
			if err != nil {
				log.Printf("Sintaksis xato: [%s] shablonida xatolik aniqlandi: %v", relPath, err)
				return nil // Bitta fayldagi xato butun serverni to'xtatib qo'ymasligi uchun davom etamiz
			}

			// Keshga saqlaymiz
			Templates[templateKey] = tmpl
			log.Printf("[%s] shabloni RAM keshiga yuklandi. Kalit: \"%s\"", relPath, templateKey)
		}
		return nil
	})

	if err != nil {
		log.Printf("Kritik xatolik: Shablonlar papkasini skanerlashda xato: %v", err)
	}
}

// GetTemplate - Xaritadan shablonni parallel oqimlarda xavfsiz o'qish funksiyasi
func GetTemplate(key string) (*template.Template, bool) {
	templatesMu.RLock()
	defer templatesMu.RUnlock()
	tmpl, exists := Templates[key]
	return tmpl, exists
}

// SlugToTitle - URL'dagi 'contest-detail' matnini 'Contest Detail' ko'rinishiga keltiruvchi SEO yordamchisi
func SlugToTitle(slug string) string {
	slug = strings.TrimSpace(slug)
	if slug == "" {
		return ""
	}

	words := strings.Split(slug, "-")
	for i, word := range words {
		if len(word) > 0 {
			words[i] = strings.ToUpper(word[:1]) + word[1:]
		}
	}
	return strings.Join(words, " ")
}
