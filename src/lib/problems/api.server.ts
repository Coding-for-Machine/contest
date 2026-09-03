import ApiProxy from "@/app/api/proxy";
import type { ProblemDetail } from "./types";

const MOCK_PROBLEMS: Record<string, ProblemDetail> = {
  "two-sum": {
    id: 1,
    slug: "two-sum",
    title: "Ikki son yig'indisi",
    desc: `Butun sonlardan iborat massiv \`nums\` va butun son \`target\` berilgan. Yig'indisi \`target\` ga teng bo'ladigan ikkita elementning indekslarini qaytaring.

Har bir kirish ma'lumotida aynan bitta yechim mavjud deb hisoblang va bir xil elementni ikki marta ishlatmang.

### Misol 1:
\`\`\`text
Kirish: nums = [2,7,11,15], target = 9
Chiqish: [0,1]
Izoh: nums[0] + nums[1] == 9, shuning uchun [0, 1] qaytariladi.
\`\`\`

### Cheklovlar:
- \`2 <= nums.length <= 10^4\`
- \`-10^9 <= nums[i] <= 10^9\`
- \`-10^9 <= target <= 10^9\`
`,
    dif: "easy",
    difficulty: "easy",
    xp: 50,
    time_l: 1.0,
    memory_l: 256,
    cate_name: "Massivlar va Xesh",
    category: "Massivlar va Xesh",
    solved: false,
    tags: [
      { id: 1, name: "Massiv" },
      { id: 2, name: "Xesh-jadval" },
    ],
    hints: [
      "Xesh-jadval (Hash Map) yordamida har bir sonni tekshirishni O(1) vaqtga tushirishingiz mumkin.",
      "Har bir element uchun (target - nums[i]) xesh-jadvalda bor yoki yo'qligini tekshiring.",
    ],
    chall: [
      "Vaqt murakkabligini O(n) ga keltirish",
      "Xotiradan O(n) foydalanish",
    ],
    exam: [
      {
        id: 1,
        input: "[2, 7, 11, 15]\n9",
        output: "[0, 1]",
        is_sample: true,
      },
      {
        id: 2,
        input: "[3, 2, 4]\n6",
        output: "[1, 2]",
        is_sample: true,
      },
      {
        id: 3,
        input: "[3, 3]\n6",
        output: "[0, 1]",
        is_sample: false,
      },
    ],
    starter_codes: {
      python: "def twoSum(nums: list[int], target: int) -> list[int]:\n    # Kodingizni bu yerga yozing\n    pass\n",
      javascript: "function twoSum(nums, target) {\n    // Kodingizni bu yerga yozing\n}\n",
      cpp: "#include <vector>\nusing namespace std;\n\nclass Solution {\npublic:\n    vector<int> twoSum(vector<int>& nums, int target) {\n        // Kodingizni bu yerga yozing\n        return {};\n    }\n};\n",
    },
    default_code: "def twoSum(nums: list[int], target: int) -> list[int]:\n    # Kodingizni bu yerga yozing\n    pass\n",
    allowed_languages: ["python", "javascript", "cpp", "java", "go"],
  },
};

export async function getProblem(slug: string): Promise<ProblemDetail | null> {
  try {
    const res = await ApiProxy.get<ProblemDetail>(`/problem/${slug}`, {
      cache: "no-store",
    });
    if (res.data) return res.data;
  } catch (err) {
    // Backend unreachable, fallback to mock
  }

  if (MOCK_PROBLEMS[slug]) return MOCK_PROBLEMS[slug];

  // Return a generated fallback for any requested slug
  return {
    ...MOCK_PROBLEMS["two-sum"],
    slug,
    title: slug.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
  };
}
