package handlers

import (
	"cfmapi/internal/models"
	"cfmapi/internal/repository"
	"context"
	"strings"
	"time"

	"github.com/gofiber/fiber/v3"
)

type SubmissionHandler struct {
	Repo          *repository.SubmissionRepository
	PistonService *repository.Client // Sizning haqiqiy Piston Clientingiz
}

func NewSubmissionHandler(repo *repository.SubmissionRepository, ps *repository.Client) *SubmissionHandler {
	return &SubmissionHandler{Repo: repo, PistonService: ps}
}

func (h *SubmissionHandler) SubmitCode(c fiber.Ctx) error {
	// 15 soniyalik umumiy kontekst tayyorlaymiz
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	// Foydalanuvchi identifikatorini tekshirish
	localID := c.Locals("telegram_id")
	if localID == nil {
		return fiber.NewError(fiber.StatusUnauthorized, "Foydalanuvchi aniqlanmadi")
	}
	telegramID, ok := localID.(int64)
	if !ok {
		return fiber.NewError(fiber.StatusInternalServerError, "Tizim xatosi: Telegram ID formati noto'g'ri")
	}

	// Request Bodyni o'qish
	dto := new(models.CreateSubmissionDTO)
	if err := c.Bind().Body(dto); err != nil {
		return fiber.NewError(fiber.StatusBadRequest, "Noto'g'ri JSON ma'lumot")
	}

	// 1. Dasturlash tilining slug nomini olish (masalan: "python", "go")
	langSlug, err := h.Repo.GetLanguageSlug(ctx, dto.LanguageID)
	if err != nil {
		return fiber.NewError(fiber.StatusBadRequest, "Dasturlash tili topilmadi")
	}

	// 2. Masalaga tegishli shablon kodlarini yuklash (LeetCode uslubi)
	executionCodes, err := h.Repo.GetExecutionCodes(ctx, dto.ProblemID, dto.LanguageID)
	if err != nil {
		return fiber.NewError(fiber.StatusInternalServerError, "Kod testi shablonlari yuklanmadi")
	}

	// 3. Kodlarni birlashtirish (TopCode + UserCode + BottomCode)
	var finalCodeBuilder strings.Builder
	if executionCodes.TopCode != nil {
		finalCodeBuilder.WriteString(*executionCodes.TopCode)
		finalCodeBuilder.WriteString("\n")
	}
	finalCodeBuilder.WriteString(dto.Code) // Foydalanuvchi yozgan algoritm funksiyasi
	finalCodeBuilder.WriteString("\n")
	if executionCodes.BottomCode != "" {
		finalCodeBuilder.WriteString(executionCodes.BottomCode)
	}

	fullCompiledCode := finalCodeBuilder.String()

	// 4. Masalaning barcha testlarini bazadan yuklash
	dbTestCases, err := h.Repo.GetTestCases(ctx, dto.ProblemID)
	if err != nil || len(dbTestCases) == 0 {
		return fiber.NewError(fiber.StatusInternalServerError, "Masalaga tegishli test caselar topilmadi")
	}

	// 5. 🔁 HAQIQIY JUDGE LOOP (BARCHA TESTLARDAN O'TKAZISH)
	var finalTestResults []models.TestResult
	overallStatus := true
	var failedMessage string

	for idx, tc := range dbTestCases {
		// Har bir test uchun Piston so'rovini tayyorlash
		pistonReq := models.PistonExecuteRequest{
			Language: langSlug,
			Version:  "*", // Eng mos keluvchi oxirgi versiya
			Files: []models.PistonFile{
				{Content: fullCompiledCode},
			},
			Stdin:          tc.InputTxt,       // tc.Input o'rniga tc.InputTxt qo'yildi
			RunTimeout:     2000,              // 2 soniya vaqt cheklovi (Time Limit)
			RunMemoryLimit: 256 * 1024 * 1024, // 256 MB xotira cheklovi (Memory Limit)
		}

		// Piston sandbox muhitida kodni xavfsiz bajarish
		res, err := h.PistonService.Execute(ctx, pistonReq)
		if err != nil {
			overallStatus = false
			failedMessage = "Internal Sandbox Error"
			break
		}

		// Natijalarni tozalash va taqqoslash
		cleanStdout := strings.TrimSpace(res.Stdout)
		cleanExpected := strings.TrimSpace(tc.OutputTxt)

		currentTestStatus := "passed"
		testPassed := false

		// Piston va Django statuslarini o'zaro bog'lash (Parser)
		if res.Status == "OK" {
			if cleanStdout == cleanExpected {
				currentTestStatus = "passed"
				testPassed = true
			} else {
				currentTestStatus = "wrong_answer"
				failedMessage = "Wrong Answer"
				overallStatus = false
			}
		} else if res.Status == "TO" {
			currentTestStatus = "time_limit_exceeded"
			failedMessage = "Time Limit Exceeded"
			overallStatus = false
		} else {
			currentTestStatus = "error"
			failedMessage = res.Message
			if failedMessage == "" && res.Stderr != "" {
				failedMessage = res.Stderr // Sintaktik xatoliklarni olish
			}
			overallStatus = false
		}

		// `models.TestResult` strukturasiga moslab ma'lumotni append qilamiz
		finalTestResults = append(finalTestResults, models.TestResult{
			TestCase:   idx + 1,
			Status:     currentTestStatus,
			Time:       int(res.WallTime.Milliseconds()),
			TestCaseID: tc.ID,
			Passed:     testPassed,
			Memory:     res.Memory,
		})

		// Bitta testdan yiqilsa, qolganlarini tekshirmasdan to'xtatamiz
		if !testPassed {
			break
		}
	}

	if overallStatus {
		failedMessage = "All test cases passed successfully"
	}

	// 7. Yakuniy natijani Django bazasiga saqlash (Sizning haqiqiy repository metodingiz)
	submissionID, err := h.Repo.Create(ctx, telegramID, *dto, overallStatus, finalTestResults)
	if err != nil {
		return fiber.NewError(fiber.StatusInternalServerError, "Natijani bazaga saqlashda xatolik yuz berdi: "+err.Error())
	}

	// 8. API Client-ga yakuniy javobni qaytarish
	return c.Status(fiber.StatusOK).JSON(fiber.Map{
		"submission_id": submissionID,
		"status":        overallStatus, // Django kutgan Boolean format (true/false)
		"message":       failedMessage,
		"tests":         finalTestResults,
	})
}

// GetMySubmissions - Foydalanuvchining shaxsiy urinishlar tarixini qaytaradi (GET /api/submissions/my)
func (h *SubmissionHandler) GetMySubmissions(c fiber.Ctx) error {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	// AuthMiddleware tomonidan yozilgan telegram_id ni olamiz
	localID := c.Locals("telegram_id")
	if localID == nil {
		return fiber.NewError(fiber.StatusUnauthorized, "Foydalanuvchi aniqlanmadi")
	}
	telegramID, ok := localID.(int64)
	if !ok {
		return fiber.NewError(fiber.StatusInternalServerError, "Telegram ID formati noto'g'ri")
	}

	// Repository'dagi FetchUserSubmissions metodini chaqiramiz (Siz yozgan repo)
	list, err := h.Repo.FetchUserSubmissions(ctx, telegramID)
	if err != nil {
		return fiber.NewError(fiber.StatusInternalServerError, "Urinishlar tarixini yuklashda xatolik yuz berdi: "+err.Error())
	}

	// Tarix ro'yxatini qaytaramiz
	return c.Status(fiber.StatusOK).JSON(list)
}
