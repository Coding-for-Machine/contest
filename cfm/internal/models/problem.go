package models

type ProblemStats struct {
	Easy   int `json:"easy"`
	Medium int `json:"medium"`
	Hard   int `json:"hard"`
}

type CompactProblemOut struct {
	ID     int      `json:"id"`
	Title  string   `json:"title"`
	Slug   string   `json:"slug"`
	Diff   string   `json:"diff"`
	Rate   float64  `json:"rate"`
	Tags   []string `json:"tags"`
	Status int      `json:"status"` // 1: yechilgan, 0: xato, -1: urinilmagan
}

type CompactProblemResponse struct {
	Total int                 `json:"total"`
	Stats *ProblemStats       `json:"stats,omitempty"` // Faqat offset=0 bo'lganda chiqishi uchun pointer
	Items []CompactProblemOut `json:"items"`
}

type CompactCategoryOut struct {
	ID   int    `json:"id"`
	Name string `json:"name"`
	Slug string `json:"slug"`
}
