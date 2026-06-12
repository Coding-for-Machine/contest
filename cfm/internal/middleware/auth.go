package middleware

import (
	"cfmapi/internal/config"
	"context"
	"errors"
	"strings"
	"time"

	"github.com/gofiber/fiber/v3"
	"github.com/golang-jwt/jwt/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// AuthMiddleware himoyalangan yo'llarni tekshirish va foydalanuvchini aniqlash uchun xizmat qiladi
func AuthMiddleware(db *pgxpool.Pool, cfg *config.Config) fiber.Handler {
	return func(c fiber.Ctx) error {
		// 1. Authorization Header'ni olish
		authHeader := c.Get("Authorization")
		if authHeader == "" {
			return fiber.NewError(fiber.StatusUnauthorized, "Authorization header topilmadi")
		}

		// 2. Bearer token formatini tekshirish
		parts := strings.Split(authHeader, " ")
		if len(parts) != 2 || parts[0] != "Bearer" {
			return fiber.NewError(fiber.StatusUnauthorized, "Noto'g'ri token formati (Bearer token kutilmoqda)")
		}
		tokenString := parts[1]

		// 3. Tokenni parsing va xavfsizlik tekshiruvi (Verification)
		token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
			// Shifrlash algoritmini tekshirish (HMAC bo'lishi shart)
			if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
				return nil, errors.New("noto'g'ri shifrlash uslubi")
			}
			return []byte(cfg.API_JWT_TOKEN), nil
		})

		if err != nil || !token.Valid {
			return fiber.NewError(fiber.StatusUnauthorized, "Token yaroqsiz yoki muddati o'tgan")
		}

		// 4. Token ichidagi ma'lumotlarni (Claims) o'qish
		claims, ok := token.Claims.(jwt.MapClaims)
		if !ok {
			return fiber.NewError(fiber.StatusUnauthorized, "Token ma'lumotlarini o'qib bo'lmadi")
		}

		// Token ichidan telegram_id ni o'qiymiz
		telegramIDFloat, ok := claims["telegram_id"].(float64)
		if !ok {
			return fiber.NewError(fiber.StatusUnauthorized, "Token ichida foydalanuvchi identifikatori yo'q")
		}
		telegramID := int64(telegramIDFloat)

		// 5. Baza (PostgreSQL) orqali foydalanuvchi faolligini tekshirish
		ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
		defer cancel()

		var isActive bool
		err = db.QueryRow(ctx, "SELECT is_active FROM users WHERE telegram_id = $1", telegramID).Scan(&isActive)
		if err != nil {
			return fiber.NewError(fiber.StatusUnauthorized, "Foydalanuvchi tizimda mavjud emas")
		}

		if !isActive {
			return fiber.NewError(fiber.StatusForbidden, "Foydalanuvchi akkaunti faolsizlantirilgan")
		}

		// 6. Keyingi handlerlar ishlata olishi uchun telegram_id ni context'ga bezarar joylaymiz
		c.Locals("telegram_id", telegramID)

		// Hamma narsa muvaffaqiyatli bo'lsa, yo'lni davom ettiramiz
		return c.Next()
	}
}
