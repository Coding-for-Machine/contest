package repository

import (
	"cfmapi/internal/models"
	"context"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

type ProblemRepository struct {
	DB *pgxpool.Pool
}

func NewProblemRepository(db *pgxpool.Pool) *ProblemRepository {
	return &ProblemRepository{DB: db}
}

// Murakkab filtrlangan masalalar ro'yxatini olish
func (r *ProblemRepository) FetchAdvancedProblems(
	ctx context.Context,
	telegramID int64,
	difficulty string,
	categoryID int,
	tagID int,
	search string,
	solved *int,
	limit, offset int,
) ([]models.CompactProblemOut, int, error) {

	// 1. Dinamik SQL generatsiya va argumentlarni massivga yig'ish
	args := []interface{}{telegramID}
	argIdx := 2

	// Subquery mantiqlari: accepted_count, total_subs, is_solved, is_failed, acceptance_rate
	// Barcha jadvallar nomlari Django standartlariga moslangan (problems_problem, submissions_submission)
	baseQuery := `
		WITH annotated_problems AS (
			SELECT 
				p.id, p.title, p.slug, p.difficulty, p.created_at,
				COALESCE((SELECT COUNT(s.id) FROM submissions_submission s WHERE s.problem_id = p.id AND s.status = true), 0) as accepted_count,
				COALESCE((SELECT COUNT(s.id) FROM submissions_submission s WHERE s.problem_id = p.id), 0) as total_subs,
				EXISTS(SELECT 1 FROM submissions_submission s JOIN users u ON s.user_id = u.id WHERE u.telegram_id = $1 AND s.problem_id = p.id AND s.status = true) as is_solved,
				EXISTS(SELECT 1 FROM submissions_submission s JOIN users u ON s.user_id = u.id WHERE u.telegram_id = $1 AND s.problem_id = p.id AND s.status = false) as is_failed
			FROM problems_problem p
			WHERE p.is_active = true AND p.problem_type = 'problem'
		),
		calculated_problems AS (
			SELECT *,
				CASE 
					WHEN total_subs = 0 THEN 0.0
					ELSE ROUND((accepted_count * 100.0 / total_subs)::numeric, 1)::float8
				END as acceptance_rate
			FROM annotated_problems
		)
		SELECT cp.*, 
		       COALESCE(
		           (SELECT json_agg(t.name) 
		            FROM problems_tags t 
		            JOIN problems_problem_tags pt ON pt.tags_id = t.id 
		            WHERE pt.problem_id = cp.id), 
		           '[]'::json
		       ) as tags_list
		FROM calculated_problems cp
		WHERE 1=1`

	// ── Djangodagi kabi filtrlarni dinamik qo'shish ──
	filterQuery := ""
	if difficulty != "" {
		filterQuery += fmt.Sprintf(" AND cp.difficulty = $%d", argIdx)
		args = append(args, difficulty)
		argIdx++
	}
	if categoryID > 0 {
		// Djangodagi p.category_id ga mos keladi
		filterQuery += fmt.Sprintf(" AND cp.id IN (SELECT id FROM problems_problem WHERE category_id = $%d)", argIdx)
		args = append(args, categoryID)
		argIdx++
	}
	if tagID > 0 {
		filterQuery += fmt.Sprintf(" AND cp.id IN (SELECT problem_id FROM problems_problem_tags WHERE tags_id = $%d)", argIdx)
		args = append(args, tagID)
		argIdx++
	}
	if search != "" {
		filterQuery += fmt.Sprintf(" AND (cp.title ILIKE $%d OR cp.id IN (SELECT id FROM problems_problem WHERE description ILIKE $%d))", argIdx, argIdx)
		args = append(args, "%"+search+"%")
		argIdx++
	}
	if solved != nil {
		if *solved == 1 {
			filterQuery += " AND cp.is_solved = true"
		} else if *solved == 0 {
			filterQuery += " AND cp.is_solved = false AND cp.is_failed = true"
		} else if *solved == -1 {
			filterQuery += " AND cp.is_solved = false AND cp.is_failed = false"
		}
	}

	// Jami sonini (Total Count) hisoblash uchun alohida count so'rovi yuboramiz
	var totalCount int
	countQuery := fmt.Sprintf("SELECT COUNT(*) FROM (%s %s) as total", baseQuery, filterQuery)
	err := r.DB.QueryRow(ctx, countQuery, args...).Scan(&totalCount)
	if err != nil {
		return nil, 0, err
	}

	// Tartiblash va Pagination (LIMIT, OFFSET) qismini ulaymiz
	finalQuery := fmt.Sprintf(`
		%s %s 
		ORDER BY cp.is_solved ASC, cp.created_at DESC 
		LIMIT $%d OFFSET $%d`, baseQuery, filterQuery, argIdx, argIdx+1)

	args = append(args, limit, offset)

	rows, err := r.DB.Query(ctx, finalQuery, args...)
	if err != nil {
		return nil, 0, err
	}
	defer rows.Close()

	var items []models.CompactProblemOut
	for rows.Next() {
		var cp struct {
			ID             int
			Title          string
			Slug           string
			Difficulty     string
			CreatedAt      time.Time
			AcceptedCount  int64
			TotalSubs      int64
			IsSolved       bool
			IsFailed       bool
			AcceptanceRate float64
			TagsList       []string
		}

		err := rows.Scan(
			&cp.ID, &cp.Title, &cp.Slug, &cp.Difficulty, &cp.CreatedAt,
			&cp.AcceptedCount, &cp.TotalSubs, &cp.IsSolved, &cp.IsFailed,
			&cp.AcceptanceRate, &cp.TagsList,
		)
		if err != nil {
			return nil, 0, err
		}

		// Djangodagi status kodlash mantiqi (1, 0, -1)
		statusCode := -1
		if cp.IsSolved {
			statusCode = 1
		} else if cp.IsFailed {
			statusCode = 0
		}

		items = append(items, models.CompactProblemOut{
			ID:     cp.ID,
			Title:  cp.Title,
			Slug:   cp.Slug,
			Diff:   cp.Difficulty,
			Rate:   cp.AcceptanceRate,
			Tags:   cp.TagsList,
			Status: statusCode,
		})
	}

	if items == nil {
		items = []models.CompactProblemOut{}
	}

	return items, totalCount, nil
}

// Faqat offset=0 bo'lganda qiyinchilik statistikalarini hisoblash
func (r *ProblemRepository) GetProblemStats(ctx context.Context) (*models.ProblemStats, error) {
	query := `
		SELECT 
			COUNT(id) FILTER (WHERE difficulty = 'easy') as easy_cnt,
			COUNT(id) FILTER (WHERE difficulty = 'medium') as medium_cnt,
			COUNT(id) FILTER (WHERE difficulty = 'hard') as hard_cnt
		FROM problems_problem
		WHERE is_active = true AND problem_type = 'problem'`

	var stats models.ProblemStats
	err := r.DB.QueryRow(ctx, query).Scan(&stats.Easy, &stats.Medium, &stats.Hard)
	if err != nil {
		return nil, err
	}
	return &stats, nil
}

// Barcha aktiv kategoriyalarni chiqarish
func (r *ProblemRepository) FetchCategories(ctx context.Context) ([]models.CompactCategoryOut, error) {
	query := `SELECT id, name, slug FROM problems_category ORDER BY name`
	rows, err := r.DB.Query(ctx, query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var categories []models.CompactCategoryOut
	for rows.Next() {
		var c models.CompactCategoryOut
		if err := rows.Scan(&c.ID, &c.Name, &c.Slug); err != nil {
			return nil, err
		}
		categories = append(categories, c)
	}

	if categories == nil {
		categories = []models.CompactCategoryOut{}
	}
	return categories, nil
}
