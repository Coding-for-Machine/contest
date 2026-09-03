package repository

import (
	"bytes"
	"cfmapi/internal/models"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"
)

type Client struct {
	hc      *http.Client
	baseURL string
}

func NewClient(baseURL string, timeout time.Duration) *Client {
	return &Client{
		hc: &http.Client{
			Timeout: timeout,
		},
		baseURL: baseURL,
	}
}

// Execute Kodni Piston qumdonida xavfsiz bajaradi va natijani tahlil qiladi
func (c *Client) Execute(ctx context.Context, req models.PistonExecuteRequest) (*models.PlatformResult, error) {
	url := fmt.Sprintf("%s/api/v2/execute", strings.TrimSuffix(c.baseURL, "/"))

	// 1. JSON-ga o'girish
	bodyBytes, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("marshal request error: %w", err)
	}

	// 2. HTTP POST So'rovini tayyorlash
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewBuffer(bodyBytes))
	if err != nil {
		return nil, fmt.Errorf("create http request error: %w", err)
	}
	httpReq.Header.Set("Content-Type", "application/json")

	// 3. So'rovni yuborish
	resp, err := c.hc.Do(httpReq)
	if err != nil {
		// Tarmoq xatosi yoki Piston serveri o'chiqligi -> XX (Tizim xatosi)
		return &models.PlatformResult{Status: "XX", Message: "Piston server disconnected"}, nil
	}
	defer resp.Body.Close()

	// 4. HTTP Status kodini tekshirish
	if resp.StatusCode != http.StatusOK {
		var errResp models.PistonExecuteResponse
		_ = json.NewDecoder(resp.Body).Decode(&errResp)
		msg := errResp.Message
		if msg == "" {
			msg = fmt.Sprintf("HTTP status %d", resp.StatusCode)
		}
		// Noto'g'ri runtime yoki port xatosi -> XX
		return &models.PlatformResult{Status: "XX", Message: msg}, nil
	}

	// 5. Muvaffaqiyatli javobni o'qish
	var pistonResp models.PistonExecuteResponse
	if err := json.NewDecoder(resp.Body).Decode(&pistonResp); err != nil {
		return &models.PlatformResult{Status: "XX", Message: "Failed to decode Piston response"}, nil
	}

	// 6. Matritsa bo'yicha Javobni Tahlil qilish (Parser Engine)
	return c.parsePistonResult(req, pistonResp), nil
}

// parsePistonResult cURL testlari asosida yozilgan eng muhim parser mantiqidir
func (c *Client) parsePistonResult(req models.PistonExecuteRequest, pResp models.PistonExecuteResponse) *models.PlatformResult {
	res := &models.PlatformResult{
		Stdout:   pResp.Run.Stdout,
		Stderr:   pResp.Run.Stderr,
		Memory:   pResp.Run.Memory,
		CpuTime:  time.Duration(pResp.Run.CpuTime) * time.Millisecond,
		WallTime: time.Duration(pResp.Run.WallTime) * time.Millisecond,
		Message:  pResp.Run.Message,
	}

	// Chiqish kodi (Exit Code) ni int ko'rinishida olish
	var exitCode int
	if codeNum, ok := pResp.Run.Code.(float64); ok {
		exitCode = int(codeNum)
	}

	// --- ⚠️ MARKERLI HIYLA: INPUT KUTISH HOlATI (IW - Input Wait) ---
	// Agar stdout ichida marker bo'lsa va stdin berilmagan bo'lsa
	if strings.Contains(pResp.Run.Stdout, "CFM_INPUT_REQUIRED") && req.Stdin == "" {
		res.Status = "IW" // Input Wait - Foydalanuvchidan input kutilyapti
		res.Message = "Program is waiting for user input"
		return res
	}

	// --- 🟣 EL (Stderr Limit Exceeded) ---
	if pResp.Run.Status == "EL" || pResp.Run.Message == "stderr length exceeded" {
		res.Status = "EL"
		return res
	}

	// --- 🔵 OL (Stdout Limit Exceeded) ---
	if pResp.Run.Status == "OL" || pResp.Run.Message == "stdout length exceeded" {
		res.Status = "OL"
		return res
	}

	// --- 🟡 TO (Time Limit Exceeded) ---
	if pResp.Run.Status == "TO" || pResp.Run.Signal == "SIGKILL" && pResp.Run.Message == "Time limit exceeded (wall clock)" {
		res.Status = "TO"
		return res
	}

	// --- 🟠 SG (Memory Limit Exceeded / Signal Killed) ---
	// cURL testida ko'rganimizdek, Python xotira to'lganda exitCode 137 qaytardi
	if pResp.Run.Signal == "SIGKILL" || exitCode == 137 {
		res.Status = "SG"
		res.Message = "Memory Limit Exceeded (Process Killed)"
		return res
	}

	// --- 🔴 RE (Runtime Error) ---
	if exitCode != 0 || pResp.Run.Stderr != "" {
		res.Status = "RE"
		return res
	}

	// --- 🟢 OK (Muvaffaqiyatli Bajarilish) ---
	res.Status = "OK"
	return res
}
