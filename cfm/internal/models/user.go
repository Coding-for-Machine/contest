package models

import "time"

// Foydalanuvchi ma'lumotlarini API orqali qaytarish uchun DTO (Data Transfer Object)
type UserProfileDTO struct {
	ID         int        `json:"id"`
	TelegramID int64      `json:"telegram_id"`
	Username   *string    `json:"username"`
	Phone      string     `json:"phone"`
	FullName   *string    `json:"full_name"`
	LastLogin  *time.Time `json:"last_login"` // Null bo'lishi mumkinligi uchun pointer
	CreatedAt  time.Time  `json:"created_at"`
	IsActive   bool       `json:"is_active"`
}
