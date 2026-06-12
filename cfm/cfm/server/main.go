package main

import (
	"context"
	"crypto/tls"
	"errors"
	"io"
	"log"
	"net"
	"os"
	"os/signal"
	"syscall"
	"time"

	"cfmapi/internal/config"
	"cfmapi/internal/database"
	"cfmapi/internal/handlers"
	"cfmapi/internal/middleware"
	"cfmapi/internal/repository"

	// Barcha middleware'lar FIBER V3 versiyada bo'lishi shart!
	"github.com/gofiber/fiber/v3"
	"github.com/gofiber/fiber/v3/middleware/cors"
	"github.com/gofiber/fiber/v3/middleware/logger"
	recoverer "github.com/gofiber/fiber/v3/middleware/recover"
	"github.com/gofiber/fiber/v3/middleware/requestid"
	"github.com/joho/godotenv"
)

func main() {
	// .env faylini yuklash
	_ = godotenv.Load()

	// Konfiguratsiyani yuklash
	cfg := config.Load()

	// 1. PostgreSQL bazasiga ulanish (Connection Pool)
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	pool, err := database.NewPostgresPool(ctx, cfg.DatabaseURL)
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}
	defer pool.Close()

	// 2. Fiber v3 Ilovasini yaratish va uning Global ErrorHandler'ini sozlash
	app := fiber.New(fiber.Config{
		AppName:      "Mening Zo'r API Ilovam v3",
		ServerHeader: "Fiber-Engine",
		BodyLimit:    10 * 1024 * 1024,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 10 * time.Second,
		IdleTimeout:  120 * time.Second,

		// Fiber v3 to'g'ri ErrorHandler uslubi
		ErrorHandler: func(c fiber.Ctx, err error) error {
			code := fiber.StatusInternalServerError
			var e *fiber.Error
			if errors.As(err, &e) {
				code = e.Code
			}
			return c.Status(code).JSON(fiber.Map{
				"error": err.Error(),
			})
		},
	})

	// 3. Global Tizim Middleware'larini ulash (Toza ketma-ketlikda)
	app.Use(recoverer.New()) // Panikalardan asraydi (Eng tepada turishi shart)
	app.Use(cors.New())      // CORS sozlamalari front-end ulanishi uchun

	// Request ID: Har bir HTTP so'rovga unikal ID beradi, loggerdan oldin turishi shart!
	app.Use(requestid.New())

	// Loglarni faylga ham saqlash uchun log faylini ochamiz
	accessLog, err := os.OpenFile("./access.log", os.O_RDWR|os.O_CREATE|os.O_APPEND, 0666)
	if err != nil {
		log.Fatalf("error opening access.log file: %v", err)
	}
	defer accessLog.Close()

	// MultiWriter: Log ham terminalga rangli chiqadi, ham faylga yoziladi
	logWriter := io.MultiWriter(os.Stdout, accessLog)

	// Mukammal Logger Konfiguratsiyasi (Toshkent vaqti bilan)
	app.Use(logger.New(logger.Config{
		Format:      "[${pid}] | ID: ${requestid} | ${time} | ${status} | ${method} | ${path} | ⏱️ ${latency}\n",
		TimeFormat:  "02-Jan-2006 15:04:05",
		TimeZone:    "Asia/Tashkent",
		Stream:      logWriter,
		ForceColors: true,
		Done: func(c fiber.Ctx, logString []byte) {
			if c.Response().StatusCode() >= 400 {
				log.Printf("⚠️ DIQQAT! Xato status qaytdi: %s", string(logString))
			}
		},
	}))

	// 5. API Marshrutlarini Guruhlash (Routing)
	api := app.Group("/api")

	// API muvaffaqiyatli ishlayotganini tekshirish uchun test endpointi
	api.Get("/status", func(c fiber.Ctx) error {
		return c.JSON(fiber.Map{"status": "OK", "db": "Connected", "protocol": c.Protocol()})
	})

	// Repositories qismi
	problemRepo := repository.NewProblemRepository(pool)
	userRepo := repository.NewUserRepository(pool)
	submissionRepo := repository.NewSubmissionRepository(pool)

	// Piston Sandbox Klientini yaratamiz
	pistonClient := repository.NewClient("http://localhost:2000", 5*time.Second)

	// Handlers qismi
	problemHandler := handlers.NewProblemHandler(problemRepo)
	userHandler := handlers.NewUserHandler(userRepo)
	submissionHandler := handlers.NewSubmissionHandler(submissionRepo, pistonClient)

	// HIMOYALANGAN YO'LLAR (Faqat toza JWT token egalari kira oladi)
	protectedAPI := api.Group("", middleware.AuthMiddleware(pool, cfg))

	protectedAPI.Get("/users/me", userHandler.GetMe)
	protectedAPI.Get("/users/:telegram_id<int>", userHandler.GetUserByTelegramID)
	protectedAPI.Get("/problems", problemHandler.GetProblems)
	protectedAPI.Get("/categories", problemHandler.GetCategories)

	// KOD YUBORISH VA URINISHLAR ENPOINTLARI
	protectedAPI.Post("/submissions", submissionHandler.SubmitCode)         // Kod yuborish
	protectedAPI.Get("/submissions/my", submissionHandler.GetMySubmissions) // Urinishlar tarixi

	// ─── TLS (HTTPS) CONFIGURATION ───
	// Sertifikat fayllarini .env yoki default yo'ldan o'qiymiz
	certPath := os.Getenv("SSL_CERT_PATH")
	keyPath := os.Getenv("SSL_KEY_PATH")
	if certPath == "" {
		certPath = "certs/ssl.cert"
	}
	if keyPath == "" {
		keyPath = "certs/ssl.key"
	}

	cer, err := tls.LoadX509KeyPair(certPath, keyPath)
	if err != nil {
		log.Fatalf("TLS sertifikatini yuklashda xatolik: %v", err)
	}

	tlsConfig := &tls.Config{Certificates: []tls.Certificate{cer}}

	// Custom TLS Listener yaratish
	ln, err := tls.Listen("tcp", ":"+cfg.ServerPort, tlsConfig)
	if err != nil {
		log.Fatalf("TLS Listener yaratishda xatolik: %v", err)
	}

	// 6. Graceful Shutdown (Serverni xavfsiz to'xtatish) sozlamasi
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

	// Serverni alohida oqimda (Goroutine) Custom TLS Listener bilan ishga tushiramiz
	go func() {
		log.Printf("Server HTTPS orqali %s portida ishga tushdi... 🚀", cfg.ServerPort)
		if err := app.Listener(ln); err != nil && !errors.Is(err, net.ErrClosed) {
			// net.ErrClosed xatosini e'tiborsiz qoldiramiz, chunki shutdown vaqtida listener yopiladi
			log.Fatalf("Server error: %v", err)
		}
	}()

	// Signal kelishini kutamiz (Ctrl+C yoki o'chirish buyrug'i)
	<-quit
	log.Println("Shutting down server...")

	// Fiber v3 da serverni o'chirishga 10 soniya vaqt berish (In-flight requestlar tugashi uchun)
	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer shutdownCancel()

	if err := app.ShutdownWithContext(shutdownCtx); err != nil {
		log.Fatalf("Server forced to shutdown: %v", err)
	}

	log.Println("Server stopped completely. Bye!")
}
