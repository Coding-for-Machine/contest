package config

import "os"

type Config struct {
	ServerPort    string
	DatabaseURL   string
	Environment   string
	API_JWT_TOKEN string
}

func Load() *Config {
	return &Config{
		ServerPort: getEnv("SERVER_PORT", "3000"),
		// 🛠 Defolt qiymatga Supabase havolangizni va IPv4 poooler portini qo'yamiz
		DatabaseURL:   getEnv("DATABASE_URL", "postgres://postgres:0020107@://supabase.com"),
		Environment:   getEnv("ENVIRONMENT", "development"),
		API_JWT_TOKEN: getEnv("API_JWT_TOKEN", "API_JWT_TOKEN"),
	}
}

func getEnv(key, fallback string) string {
	if value, exists := os.LookupEnv(key); exists {
		return value
	}
	return fallback
}
