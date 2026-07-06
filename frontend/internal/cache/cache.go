package cache

import (
	"context"
	"time"

	"github.com/allegro/bigcache/v3"
)

type Cache struct {
	Memory *bigcache.BigCache
}

func NewCache() (*Cache, error) {
	config := bigcache.Config{
		Shards:             1024,
		LifeWindow:         5 * time.Minute,
		CleanWindow:        1 * time.Minute,
		MaxEntriesInWindow: 1000 * 10 * 60,
		MaxEntrySize:       500,
		Verbose:            false,
		HardMaxCacheSize:   512,
	}

	client, err := bigcache.New(context.Background(), config)
	if err != nil {
		return nil, err
	}

	return &Cache{Memory: client}, nil
}

// SetString - Keshga string ma'lumot yozish (Masalan HTML sahifalar uchun)
func (c *Cache) SetString(key string, value string) error {
	return c.Memory.Set(key, []byte(value))
}

// GetString - Keshdan string ma'lumotni o'qish
func (c *Cache) GetString(key string) (string, error) {
	bytes, err := c.Memory.Get(key)
	if err != nil {
		return "", err
	}
	return string(bytes), nil
}
