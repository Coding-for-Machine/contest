package models

import "time"

// TestResult - Test case'larning batafsil natijalari strukturasi.
// Bu struktura Django 'submissions_submission' jadvalidagi 'test_results' (JSONField) ichiga yoziladi.
type TestResult struct {
	TestCase   int    `json:"test_case"`              // Test raqami (1, 2, 3...) -> Django help_text formatiga mos
	Status     string `json:"status"`                 // passed, wrong_answer, time_limit_exceeded, error
	Time       int    `json:"time"`                   // Bajarilish vaqti millisekundlarda (int)
	TestCaseID int64  `json:"test_case_id,omitempty"` // Bazadagi haqiqiy test ID raqami
	Passed     bool   `json:"passed"`                 // Testdan o'tdimi (true/false)
	Memory     int64  `json:"memory"`                 // Ishlatilgan xotira (baytlarda)
}

// CreateSubmissionDTO - Yangi kod urinishini qabul qilish uchun DTO (HTTP POST request)
type CreateSubmissionDTO struct {
	ProblemID  int    `json:"problem_id"`
	ContestID  *int   `json:"contest_id"` // Null bo'lishi mumkinligi uchun pointer
	Code       string `json:"code"`
	LanguageID int    `json:"language_id"`
}

// SubmissionListDTO - Urinishlar tarixi lentalari uchun ixcham model (HTTP GET list)
type SubmissionListDTO struct {
	ID           int       `json:"id"`
	TelegramID   int64     `json:"telegram_id"`
	ProblemTitle string    `json:"problem_title"`
	LanguageName string    `json:"language_name"`
	Status       bool      `json:"status"` // Django'dagi BooleanField ustuniga mos (true=Accepted, false=Failed)
	SubmittedAt  time.Time `json:"submitted_at"`
}

// ExecutionTestCase - Django 'problems_executiontestcase' jadvalini o'qish uchun model
type ExecutionTestCase struct {
	TopCode    *string `json:"top_code"` // Null bo'lishi mumkinligi uchun pointer
	BottomCode string  `json:"bottom_code"`
}

// DBTestCase - Django 'problems_testcase' jadvalini o'qish uchun model
type DBTestCase struct {
	ID        int64  `json:"id"` // Handlerda tc.ID xato bermasligi uchun ID qo'shildi
	InputTxt  string `json:"input_txt"`
	OutputTxt string `json:"output_txt"`
}
