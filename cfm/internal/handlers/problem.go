package handlers

import (
	"cfmapi/internal/models"
	"cfmapi/internal/repository"
	"context"
	"strconv"
	"time"

	"github.com/gofiber/fiber/v3"
)

type ProblemHandler struct {
	Repo *repository.ProblemRepository
}

func NewProblemHandler(repo *repository.ProblemRepository) *ProblemHandler {
	return &ProblemHandler{Repo: repo}
}

// GET /api/problems (Himoyalangan va filtrlangan)
func (h *ProblemHandler) GetProblems(c fiber.Ctx) error {
	ctx, cancel := context.WithTimeout(context.Background(), 6*time.Second)
	defer cancel()

	// Tizimga kirgan foydalanuvchining Telegram ID sini olamiz (AuthMiddleware orqali kelgan)
	localID := c.Locals("telegram_id")
	if localID == nil {
		return fiber.NewError(fiber.StatusFound, "Foydalanuvchi aniqlanmadi")
	}
	telegramID := localID.(int64)

	// Query parametrlarni o'qish
	difficulty := c.Query("difficulty", "")
	categoryID, _ := strconv.Atoi(c.Query("category_id", "0"))
	tagID, _ := strconv.Atoi(c.Query("tag_id", "0"))
	search := c.Query("search", "")
	limit, _ := strconv.Atoi(c.Query("limit", "20"))
	offset, _ := strconv.Atoi(c.Query("offset", "0"))

	var solvedPtr *int
	if solvedStr := c.Query("solved", ""); solvedStr != "" {
		s, err := strconv.Atoi(solvedStr)
		if err == nil {
			solvedPtr = &s
		}
	}

	// Repository so'rovini amalga oshirish
	items, total, err := h.Repo.FetchAdvancedProblems(ctx, telegramID, difficulty, categoryID, tagID, search, solvedPtr, limit, offset)
	if err != nil {
		return fiber.NewError(fiber.StatusInternalServerError, "Masalalarni yuklashda xato: "+err.Error())
	}

	// Agar offset == 0 bo'lsa stats yuklanadi (Trafikni tejash)
	var statsData *models.ProblemStats = nil
	if offset == 0 {
		statsData, _ = h.Repo.GetProblemStats(ctx)
	}

	return c.JSON(models.CompactProblemResponse{
		Total: total,
		Stats: statsData,
		Items: items,
	})
}

// GET /api/categories (Hamma uchun ochiq minimal kategoriyalar)
func (h *ProblemHandler) GetCategories(c fiber.Ctx) error {
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()

	categories, err := h.Repo.FetchCategories(ctx)
	if err != nil {
		return fiber.NewError(fiber.StatusInternalServerError, "Kategoriyalarni yuklashda xato: "+err.Error())
	}

	return c.JSON(categories)
}
