package cache

import (
	"context"
	"time"

	"github.com/allegro/bigcache/v3"
)

type Cache struct {
	Memory *bigcache.BigCache
}

func NewCache() (*Cache, error) {
	// BigCache rasmiy konfiguratsiya sozlamalari (Documentation)
	config := bigcache.Config{
		// Shards: Keshni parallel bo'laklarga ajratish.
		// Qoida: Har bir bo'lak alohida Mutex qulfiga ega. Raqam qanchalik katta bo'lsa,
		// yuqori yuklamada (High Load) qulflar to'qnashuvi shunchalik kamayadi va API tezlashadi.
		// Majburiyat: Qiymat albatta 2 ning darajasi bo'lishi shart (2, 4, 8, ... 512, 1024).
		Shards: 1024,

		// LifeWindow: Ma'lumotning keshda tirik turish muddati (TTL).
		// Qoida: Element keshga muvaffaqiyatli yozilgan soniyadan boshlab hisoblanadi.
		// 5 daqiqa o'tgach, element eskirgan (expired) hisoblanadi va Get so'rovida topilmaydi.
		LifeWindow: 5 * time.Minute,

		// CleanWindow: Fondagi o'lik ma'lumotlarni tozalash goroutinasining ishlash davri.
		// Qoida: Har 1 daqiqada tiker ishga tushib, xotirani tozalaydi.
		// Agar 0 qo'yilsa, fonda avtomatik tozalash o'chadi (faqat xotira to'lganda tozalanadi).
		CleanWindow: 1 * time.Minute,

		// MaxEntriesInWindow: LifeWindow ichida keshga yozilishi kutilayotgan elementlar soni.
		// Qoida: 1000 * 10 * 60 = 600,000 ta element. BigCache xotiradan boshidanoq
		// joy ajratib qo'yishi (pre-allocation) uchun kerak. Bu ishlash davomida xotirani
		// qayta-qayta kengaytirishga ketadigan ortiqcha vaqt va resursni tejaydi.
		MaxEntriesInWindow: 1000 * 10 * 60,

		// MaxEntrySize: Keshga yoziladigan bitta elementning taxminiy maksimal hajmi (baytlarda).
		// Qoida: MaxEntriesInWindow bilan birga ishlab, boshlang'ich RAM hajmini hisoblaydi.
		// Agar element hajmi 500 baytdan oshib ketsa ham xato bermaydi, kesh dinamik kengayadi.
		MaxEntrySize: 500,

		// Verbose: Keshning ichki diagnostika loglarini terminalga chiqarish.
		// Qoida: Real production serverlarda loglar keraksiz to'lib ketmasligi uchun false qilinadi.
		Verbose: false,

		// HardMaxCacheSize: Kesh xotirasining Megabayt (MB) hisobidagi eng yuqori chegarasi.
		// Qoida: Serverni Out of Memory (OOM) bo'lib qulashidan saqlovchi asosiy xavfsizlik filtri.
		// Kesh 512 MB ga yetganda, yangi ma'lumot kelsa server o'chmaydi, eng eski ma'lumotlar o'chiriladi.
		// Agar xotirani cheklash kerak bo'lmasa, 0 qo'yiladi.
		HardMaxCacheSize: 512,
	}

	// bigcache/v3 versiyada New funksiyasi birinchi argumentga majburiy Context qabul qiladi
	client, err := bigcache.New(context.Background(), config)
	if err != nil {
		return nil, err
	}

	return &Cache{Memory: client}, nil
}
