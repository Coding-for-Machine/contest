package repository

import (
	"cfmapi/internal/models"
	"context"

	"github.com/jackc/pgx/v5/pgxpool"
)

type UserRepository struct {
	DB *pgxpool.Pool
}

func NewUserRepository(db *pgxpool.Pool) *UserRepository {
	return &UserRepository{DB: db}
}

// Telegram ID bo'yicha foydalanuvchini bazadan qidirish
func (r *UserRepository) GetByTelegramID(ctx context.Context, telegramID int64) (*models.UserProfileDTO, error) {
	var u models.UserProfileDTO

	// Django loyihangizdagi 'users' jadvalidan ma'lumotlarni aniq tartibda o'qiymiz
	query := `
		SELECT id, telegram_id, username, phone, full_name, last_login, created_at, is_active 
		FROM users 
		WHERE telegram_id = $1`

	// Scan funksiyasi endi *string maydonlarga NULL qiymatlarni muammosiz joylaydi
	err := r.DB.QueryRow(ctx, query, telegramID).Scan(
		&u.ID,
		&u.TelegramID,
		&u.Username, // *string NULL kelishiga tayyor
		&u.Phone,
		&u.FullName,  // *string NULL kelishiga tayyor
		&u.LastLogin, // *time.Time NULL kelishiga tayyor
		&u.CreatedAt,
		&u.IsActive,
	)

	if err != nil {
		return nil, err
	}

	return &u, nil
}
