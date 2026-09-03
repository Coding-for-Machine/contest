package handler

import (
	"webserver/internal/cache"
)

// App - Loyihadagi barcha handlerlar foydalanadigan umumiy konteyner
type App struct {
	Cache *cache.Cache
	// Kelajakda bu yerga DB *sql.DB yoki Logger qo'shish juda oson bo'ladi
}

// NewApp - Umumiy konteynerni tashabbuslashtirish
func NewApp(c *cache.Cache) *App {
	return &App{
		Cache: c,
	}
}
