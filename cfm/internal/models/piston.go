package models

import "time"

// PistonExecuteRequest Piston API-ga yuboriladigan so'rov strukturasi
type PistonExecuteRequest struct {
	Language       string       `json:"language"`
	Version        string       `json:"version"`
	Files          []PistonFile `json:"files"`
	Stdin          string       `json:"stdin,omitempty"`
	RunTimeout     int          `json:"run_timeout,omitempty"`      // millisekundda
	RunMemoryLimit int64        `json:"run_memory_limit,omitempty"` // baytlarda
}

type PistonFile struct {
	Content string `json:"content"`
}

// PistonExecuteResponse Piston API-dan qaytadigan xom javob strukturasi
type PistonExecuteResponse struct {
	Language string `json:"language"`
	Version  string `json:"version"`
	Run      struct {
		Stdout   string      `json:"stdout"`
		Stderr   string      `json:"stderr"`
		Code     interface{} `json:"code"` // int yoki null bo'lishi mumkin
		Signal   string      `json:"signal"`
		Memory   int64       `json:"memory"`
		Message  string      `json:"message"`
		Status   string      `json:"status"` // Piston o'zining ichki statusi (agar bo'lsa)
		CpuTime  int         `json:"cpu_time"`
		WallTime int         `json:"wall_time"`
	} `json:"run"`
	Message string `json:"message,omitempty"` // Ichki xatoliklar uchun (XX)
}

// PlatformResult Bizning Go backend tizim ishlab chiqadigan yakuniy professional natija
type PlatformResult struct {
	Status   string        `json:"status"` // OK, RE, SG, TO, OL, EL, XX, IW (Input Wait)
	Stdout   string        `json:"stdout"`
	Stderr   string        `json:"stderr"`
	Memory   int64         `json:"memory"`
	CpuTime  time.Duration `json:"cpu_time"`
	WallTime time.Duration `json:"wall_time"`
	Message  string        `json:"message"`
}
