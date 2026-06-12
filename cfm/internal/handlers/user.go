package handlers

import (
	"cfmapi/internal/repository"
	"context"
	"errors"
	"strconv"
	"time"

	"github.com/gofiber/fiber/v3"
	"github.com/jackc/pgx/v5"
)

type UserHandler struct {
	Repo *repository.UserRepository
}

func NewUserHandler(repo *repository.UserRepository) *UserHandler {
	return &UserHandler{Repo: repo}
}

// 1. GET /api/users/me (Tizimga kirgan foydalanuvchining o'z profili)
func (h *UserHandler) GetMe(c fiber.Ctx) error {
	ctx, cancel := context.WithTimeout(context.Background(), 4*time.Second)
	defer cancel()

	// AuthMiddleware yozib ketgan context ma'lumotini o'qiymiz
	localID := c.Locals("telegram_id")
	if localID == nil {
		return fiber.NewError(fiber.StatusUnauthorized, "Foydalanuvchi aniqlanmadi")
	}
	telegramID := localID.(int64)

	// Bazadan o'z profilini tortamiz
	userProfile, err := h.Repo.GetByTelegramID(ctx, telegramID)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return fiber.NewError(fiber.StatusNotFound, "Profilingiz topilmadi")
		}
		return fiber.NewError(fiber.StatusInternalServerError, "Baza xatoligi: "+err.Error())
	}

	return c.JSON(userProfile)
}

// 2. GET /api/users/:telegram_id (Boshqa foydalanuvchi profilini ko'rish)
func (h *UserHandler) GetUserByTelegramID(c fiber.Ctx) error {
	ctx, cancel := context.WithTimeout(context.Background(), 4*time.Second)
	defer cancel()

	// URL parametridan telegram_id ni o'qiymiz
	telegramIDStr := c.Params("telegram_id")
	telegramID, err := strconv.ParseInt(telegramIDStr, 10, 64)
	if err != nil {
		return fiber.NewError(fiber.StatusBadRequest, "Noto'g'ri Telegram ID formati")
	}

	// Repository orqali qidiramiz
	userProfile, err := h.Repo.GetByTelegramID(ctx, telegramID)
	if err != nil {
		// Baza ichidan qidirilgan qator topilmagan holatni ushlaymiz
		if errors.Is(err, pgx.ErrNoRows) {
			return fiber.NewError(fiber.StatusNotFound, "Bunday Telegram ID ga ega foydalanuvchi topilmadi")
		}
		return fiber.NewError(fiber.StatusInternalServerError, "Baza xatoligi: "+err.Error())
	}

	// 🔒 Xavfsizlik bo'yicha tavsiya: Agar begona odam profilini ko'rayotgan bo'lsa,
	// telefon raqamini yashirib (yoki yulduzcha qilib) jo'natish mantiqini shu yerda yozish mumkin:
	// userProfile.Phone = "+998*****"

	return c.JSON(userProfile)
}
