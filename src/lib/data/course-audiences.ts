export interface CourseAudienceTab {
  id: string;
  label: string;
  features: string[];
}

export interface CourseAudienceData {
  defaultTab: string;
  tabs: CourseAudienceTab[];
}

const DEFAULT_AUDIENCE: CourseAudienceData = {
  defaultTab: "beginners",
  tabs: [
    {
      id: "beginners",
      label: "Boshlovchilar uchun",
      features: [
        "Dasturlash asoslarini noldan o'rganishni xohlovchilar",
        "Algoritmik fikrlashni shakllantirish niyatidagi talabalar",
        "Amaliy masalalar orqali bilimini mustahkamlashni istaganlar",
      ],
    },
    {
      id: "students",
      label: "Talabalar & O'quvchilar",
      features: [
        "Olimpiada va musobaqalarga tayyorgarlik ko'rayotganlar",
        "Universitet imtihonlariga tayyorlanayotganlar",
        "Portfolio va xalqaro sertifikatga ega bo'lishni xohlovchilar",
      ],
    },
    {
      id: "developers",
      label: "Junior dasturchilar",
      features: [
        "Texnik intervyularga (FAANG / mahalliy IT) tayyorlanayotganlar",
        "Ma'lumotlar tuzilmalari va murakkab algoritmlarni chuqurlashtirmoqchi bo'lganlar",
        "Kod samaradorligi (vaqt va xotira)ni optimallashtirishni o'rganuvchilar",
      ],
    },
  ],
};

const AUDIENCE_MAP: Record<string, CourseAudienceData> = {
  default: DEFAULT_AUDIENCE,
};

export function getCourseAudience(slug: string): CourseAudienceData {
  return AUDIENCE_MAP[slug] ?? DEFAULT_AUDIENCE;
}
