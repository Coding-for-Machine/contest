package main

import (
	"crypto/tls"
	"log"
	"net/http"
	"os"
	"time"
	"webserver/internal/cache"
	"webserver/internal/config"
	"webserver/internal/handler"
	"webserver/internal/middleware"

	"golang.org/x/net/http2"
)

func main() {
	// Joriy ishchi papkani aniqlash
	wd, err := os.Getwd()
	if err != nil {
		log.Fatalf("Kritik xatolik: %v", err)
	}

	// Shablonlarni RAM keshga yuklash
	config.LoadTemplates(wd)

	mux := http.NewServeMux()

	// 1. Statik assetlarni xavfsiz tarqatish
	fileServer := http.StripPrefix("/assets/", http.FileServer(http.Dir(wd+"/assets")))
	mux.Handle("/assets/", fileServer)

	// 2. SEO Tizimi uchun muhim ildiz statik fayllari
	mux.HandleFunc("/robots.txt", func(w http.ResponseWriter, r *http.Request) {
		http.ServeFile(w, r, wd+"/robots.txt")
	})
	mux.HandleFunc("/sitemap.xml", func(w http.ResponseWriter, r *http.Request) {
		http.ServeFile(w, r, wd+"/sitemap.xml")
	})

	// Bitta umumiy keshni yaratamiz
	appCache, _ := cache.NewCache()

	// Keshni hamma handler obyektlariga Dependency Injection orqali bog'laymiz
	homeHandler := handler.NewHomeHandler(appCache)
	problemsHandler := handler.NewProblemsHandler(appCache)
	contestHandler := handler.NewContestHandler(appCache)
	profileHandler := handler.NewProfileHandler(appCache) // Katta harf bilan to'g'rilandi

	// 3. Sahifalar yo'nalishlari
	mux.HandleFunc("/", homeHandler.Home)
	mux.HandleFunc("/login", handler.Login)

	// Masalalar sahifalari
	mux.HandleFunc("/problems", problemsHandler.GetProblems)
	mux.HandleFunc("/problems/", problemsHandler.GetProblems)

	// Musobaqalar sahifalari
	mux.HandleFunc("/contests", contestHandler.GetContests)
	mux.HandleFunc("/contests/", contestHandler.GetContests)

	// Profile page uchin (TUZATILGAN QISM)
	// Go ServeMux'da oxiri "/" bilan tugasa, undan keyin kelgan har qanday matnni
	// (masalan: /u/asadbek, /u/john) avtomatik ravishda ushbu handlerga yo'naltiradi.
	mux.HandleFunc("/u/", profileHandler.GetProfile)

	// Barcha routelarni umumiy middleware-dan o'tkazish
	siteHandler := middleware.GlobalMiddleware(mux)

	// TLS va HTTP/2 Konfiguratsiyasi (Xavfsizlik va Tezlik standarti)
	tlsConfig := &tls.Config{
		MinVersion:       tls.VersionTLS13,
		CurvePreferences: []tls.CurveID{tls.X25519, tls.CurveP256},
		NextProtos:       []string{"h2", "http/1.1"},
	}

	server := &http.Server{
		Addr:              ":8080",
		Handler:           siteHandler,
		TLSConfig:         tlsConfig,
		ReadTimeout:       4 * time.Second,
		ReadHeaderTimeout: 1 * time.Second,
		WriteTimeout:      12 * time.Second,
		IdleTimeout:       45 * time.Second,
	}

	http2Server := &http2.Server{
		MaxConcurrentStreams: 250,
		IdleTimeout:          45 * time.Second,
	}

	if err := http2.ConfigureServer(server, http2Server); err != nil {
		log.Fatalf("HTTP/2 Server xatoligi: %v", err)
	}

	log.Println("CFM Loyihasi Clean Architecture asosida HTTPS (:8080) da ishlamoqda...")
	log.Fatal(server.ListenAndServeTLS("cert.pem", "key.pem"))
}
