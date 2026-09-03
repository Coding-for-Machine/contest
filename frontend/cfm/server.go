package main

import (
	"context"
	"crypto/tls"
	"errors"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"webserver/internal/cache"
	"webserver/internal/config"
	"webserver/internal/handler"
	"webserver/internal/middleware"

	"golang.org/x/net/http2"
)

func main() {
	// 1. Joriy ishchi papkani aniqlash
	wd, err := os.Getwd()
	if err != nil {
		log.Fatalf("❌ Kritik xatolik: Joriy papkani aniqlab bo'lmadi: %v", err)
	}

	// 2. Shablonlarni RAM keshga chuqurligidan qat'iy nazar avtomat yuklash
	config.LoadTemplates(wd)

	// 3. Yagona umumiy BigCache (Shared Memory Cache) tizimini yaratish
	appCache, err := cache.NewCache()
	if err != nil {
		log.Fatalf("❌ Kesh tizimini ishga tushirishda xatolik: %v", err)
	}

	// 4. Dependency Injection - Barcha handlerlar uchun yagona umumiy konteyner
	app := handler.NewApp(appCache)

	// 5. Asosiy Router (ServeMux)
	mux := http.NewServeMux()

	// =================================================================
	// STATIK VA SEO FAYLLARINI TARQATISH
	// =================================================================
	// ⚠️ DIQQAT: Loyiha daraxtingizda ildizda ham 'assets', ham 'static' papkalari bor.
	// Ikkalasi ham brauzerda muammosiz ochilishi uchun ruterlar ulandi:

	// /assets/ prefiksi uchun (css/style.css, js/main.js va h.k.)
	assetsServer := http.StripPrefix("/assets/", http.FileServer(http.Dir(wd+"/assets")))
	mux.Handle("/assets/", assetsServer)

	// /static/ prefiksi uchun (css/github-markdown.css, img/cfm_logo.webp va h.k.)
	staticServer := http.StripPrefix("/static/", http.FileServer(http.Dir(wd+"/static")))
	mux.Handle("/static/", staticServer)

	// SEO qidiruv botlari uchun muhim ochiq fayllar
	mux.HandleFunc("/robots.txt", func(w http.ResponseWriter, r *http.Request) {
		http.ServeFile(w, r, wd+"/robots.txt")
	})
	mux.HandleFunc("/sitemap.xml", func(w http.ResponseWriter, r *http.Request) {
		http.ServeFile(w, r, wd+"/sitemap.xml")
	})

	// =================================================================
	// HTML SAHIFALAR MARSHRUTLARI (RENDER)
	// =================================================================
	// Bosh sahifa va Login
	mux.HandleFunc("/", app.Home)
	mux.HandleFunc("/login", handler.Newlogin)

	// Masalalar sahifalari
	mux.HandleFunc("/problems", app.GetProblems)

	// Masala tafsiloti (Unga GetProblemDetail bog'lanishi shart!)
	mux.HandleFunc("/problem/", app.GetProblemDetail)

	// Testlar sahifalari
	mux.HandleFunc("/tests", app.Gettests)
	mux.HandleFunc("/test/", app.GetTestDetail)
	mux.HandleFunc("/tests/", app.GetTestExam)
	mux.HandleFunc("/tests/result", app.GetTestResult)
	// Musobaqalar sahifalari
	mux.HandleFunc("/contests", app.GetContests)
	mux.HandleFunc("/contest/", app.GetContests)

	// Kurslar va interaktiv darslar sahifalari
	mux.HandleFunc("/courses", app.GetCourses)
	mux.HandleFunc("/course/", app.GetCourseDetail)
	mux.HandleFunc("/lesson/", app.GetLessonDetail)

	// Dinamik profil sahifalari (Masalan: /u/asadbek)
	mux.HandleFunc("/u/", app.GetProfile)

	// =================================================================
	// MIDDLEWARE VA XAVFSIZLIK SOZLAMALARI
	// =================================================================
	// Toza, xavfsiz va Gzip siqishga ega middleware zanjiri
	siteHandler := middleware.GlobalMiddleware(mux)

	// TLS 1.3 standarti (Maksimal xavfsizlik va Google SEO talablariga mos)
	tlsConfig := &tls.Config{
		MinVersion:       tls.VersionTLS13,
		CurvePreferences: []tls.CurveID{tls.X25519, tls.CurveP256},
		NextProtos:       []string{"h2", "http/1.1"}, // HTTP/2-ni majburlash
	}

	server := &http.Server{
		Addr:              ":8081",
		Handler:           siteHandler,
		TLSConfig:         tlsConfig,
		ReadTimeout:       4 * time.Second,
		ReadHeaderTimeout: 1 * time.Second,
		WriteTimeout:      12 * time.Second,
		IdleTimeout:       45 * time.Second,
	}

	// HTTP/2 Server yuqori oqim konfiguratsiyasi
	http2Server := &http2.Server{
		MaxConcurrentStreams: 250,
		IdleTimeout:          45 * time.Second,
	}

	if err := http2.ConfigureServer(server, http2Server); err != nil {
		log.Fatalf("❌ HTTP/2 Server konfiguratsiya xatoligi: %v", err)
	}

	// Serverni alohida goroutina (oqim) ichida xavfsiz yurgizish
	go func() {
		log.Println("🚀 CFM Monolit Server HTTPS (:8081) portida muvaffaqiyatli ishga tushdi...")
		if err := server.ListenAndServeTLS("cert.pem", "key.pem"); err != nil && !errors.Is(err, http.ErrServerClosed) {
			log.Fatalf("❌ Render Server qulash xatoligi: %v", err)
		}
	}()

	// =================================================================
	// GRACEFUL SHUTDOWN (Serverni Yo'qotishlarsiz To'xtatish)
	// =================================================================
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, os.Interrupt, syscall.SIGTERM)

	<-stop // Server o'chirilish signali kelishini kutadi (Ctrl+C yoki kill)
	log.Println("\n🛑 To'xtatish signali olindi. Chala so'rovlar yakunlanishi kutilmoqda...")

	// Foydalanuvchilarning chala qolgan so'rovlarini uzib qo'ymaslik uchun 15 soniya vaqt
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	if err := server.Shutdown(ctx); err != nil {
		log.Printf("⚠️ Serverni yopishda xatolik yuz berdi: %v", err)
	}

	log.Println("✅ Server muvaffaqiyatli to'xtatildi. Dastur toza yakunlandi.")
}
