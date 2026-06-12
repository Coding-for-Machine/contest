package repository

import (
	"cfmapi/internal/models"
	"context"
	"encoding/json"

	"github.com/jackc/pgx/v5/pgxpool"
)

type SubmissionRepository struct {
	DB *pgxpool.Pool
}

func NewSubmissionRepository(db *pgxpool.Pool) *SubmissionRepository {
	return &SubmissionRepository{DB: db}
}

// 1. Yangi urinishni bazaga yozish (INSERT)
func (r *SubmissionRepository) Create(ctx context.Context, telegramID int64, dto models.CreateSubmissionDTO, status bool, results []models.TestResult) (int, error) {
	// Aytaylik, natijalarni JSON formatga o'giramiz
	jsonResults, err := json.Marshal(results)
	if err != nil {
		return 0, err
	}

	// Avval foydalanuvchining ichki ID'sini users jadvalidan aniqlab olamiz
	var userID int
	err = r.DB.QueryRow(ctx, "SELECT id FROM users WHERE telegram_id = $1", telegramID).Scan(&userID)
	if err != nil {
		return 0, err
	}

	// Django 'submissions_submission' jadvaliga yozish so'rovi
	query := `
		INSERT INTO submissions_submission (user_id, problem_id, contest_id, code, language_id, status, test_results, submitted_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
		RETURNING id`

	var submissionID int
	err = r.DB.QueryRow(ctx, query, userID, dto.ProblemID, dto.ContestID, dto.Code, dto.LanguageID, status, jsonResults).Scan(&submissionID)
	if err != nil {
		return 0, err
	}

	return submissionID, nil
}

// 2. Foydalanuvchining shaxsiy urinishlar tarixini olish (Faqat oxirgi 20 tasi)
func (r *SubmissionRepository) FetchUserSubmissions(ctx context.Context, telegramID int64) ([]models.SubmissionListDTO, error) {
	query := `
		SELECT 
			s.id, u.telegram_id, p.title, l.name, s.status, s.submitted_at
		FROM submissions_submission s
		JOIN users u ON s.user_id = u.id
		JOIN problems_problem p ON s.problem_id = p.id
		JOIN problems_language l ON s.language_id = l.id
		WHERE u.telegram_id = $1
		ORDER BY s.submitted_at DESC
		LIMIT 20`

	rows, err := r.DB.Query(ctx, query, telegramID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var submissions []models.SubmissionListDTO
	for rows.Next() {
		var s models.SubmissionListDTO
		err := rows.Scan(&s.ID, &s.TelegramID, &s.ProblemTitle, &s.LanguageName, &s.Status, &s.SubmittedAt)
		if err != nil {
			return nil, err
		}
		submissions = append(submissions, s)
	}

	if submissions == nil {
		submissions = []models.SubmissionListDTO{}
	}
	return submissions, nil
}

// 1. Masala va tilga tegishli Top va Bottom kodlarni o'qish
func (r *SubmissionRepository) GetExecutionCodes(ctx context.Context, problemID, langID int) (*models.ExecutionTestCase, error) {
	var etc models.ExecutionTestCase
	// Django ko'pga-ko'p va unique jadvallarni nomlash standarti: problems_executiontestcase
	query := `
		SELECT top_code, bottom_code 
		FROM problems_executiontestcase 
		WHERE problem_id = $1 AND language_id = $2 
		LIMIT 1`

	err := r.DB.QueryRow(ctx, query, problemID, langID).Scan(&etc.TopCode, &etc.BottomCode)
	if err != nil {
		return nil, err
	}
	return &etc, nil
}

// 2. Masalaga tegishli BARCHA test-caselarni o'qib kelish
func (r *SubmissionRepository) GetTestCases(ctx context.Context, problemID int) ([]models.DBTestCase, error) {
	query := `SELECT input_txt, output_txt FROM problems_testcase WHERE problem_id = $1`

	rows, err := r.DB.Query(ctx, query, problemID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var cases []models.DBTestCase
	for rows.Next() {
		var tc models.DBTestCase
		if err := rows.Scan(&tc.InputTxt, &tc.OutputTxt); err != nil {
			return nil, err
		}
		cases = append(cases, tc)
	}
	return cases, nil
}

// 3. Qo'shimcha yordam: language_id orqali Piston tushunadigan til nomini aniqlash (e.g., 1 -> "python")
func (r *SubmissionRepository) GetLanguageSlug(ctx context.Context, langID int) (string, error) {
	var slug string
	err := r.DB.QueryRow(ctx, "SELECT slug FROM problems_language WHERE id = $1", langID).Scan(&slug)
	return slug, err
}
