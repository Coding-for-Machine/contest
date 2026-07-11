# sse.py
"""
Global SSE (Server-Sent Events) endpoint.

Bu endpoint HAR BIR FOYDALANUVCHI uchun BITTA doimiy ochiq HTTP ulanish
bo'lib xizmat qiladi. U hech narsa "hisoblamaydi" — shunchaki Redisning
`sse:user:{user_id}` kanalini tinglab turadi va u yerga PUBLISH qilingan
har qanday xabarni, o'zgarishsiz, SSE formatida ("data: <xabar>\n\n")
brauzerga uzatib beradi.

Nega EventSource (brauzer tomoni) GET so'rov ishlatadi, POST emas?
Chunki `EventSource` — brauzerning ICHKI (native) API'si, u faqat GET
so'rovlarni qo'llab-quvvatlaydi va custom header (masalan Authorization)
yubora olmaydi. Shu sababli autentifikatsiya uchun token QUERY PARAM
orqali beriladi (`?token=...`) — main.js'dagi `RCEvents.connect()`
buni avtomatik qo'shadi.

Nega bitta kanal (sse:user:{id}) barcha voqealar uchun ishlatiladi
(alohida "run" kanali, alohida "submit" kanali emas)?
Chunki foydalanuvchi bitta paytda bir nechta narsa qilishi mumkin (bir
nechta tab, run va submit ketma-ket) — hammasini BITTA ulanish orqali
olib kelib, ichidagi "task_id" maydoni bo'yicha frontendda ажратиш ancha
sodda va samarali, ko'p ulanish ochishdan ko'ra.
"""

import redis.asyncio as aioredis
from django_bolt import Router, Request, Depends
from django_bolt.responses import StreamingResponse
from baseuser.authenticate import get_current_user_from_url
from baseuser.models import BaseUser

sse_router = Router(tags=["sse"])

REDIS_URL = "redis://localhost:6379/0"


@sse_router.get("/events/stream/")
async def event_stream(request: Request, request_user: BaseUser = Depends(get_current_user_from_url)):
    """
    Global SSE oqimi.

    `get_current_user` dependency — bu yerda ODATDAGI Authorization
    header'dan EMAS, balki `?token=...` query parametridan token o'qiy
    olishi kerak (chunki EventSource header yubora olmaydi). Agar sizning
    `get_current_user`ingiz faqat header'dan o'qisa, shu funksiya uchun
    maxsus variant yozib, uni shu yerda ishlating:

        async def get_current_user_from_query(request: Request) -> BaseUser:
            token = request.query_params.get("token")
            ...  # tokenni tekshirib, foydalanuvchini qaytaring
    """
    channel = f"sse:user:{request_user.id}"

    async def event_generator():
        """
        Redis pub/sub'ni tinglovchi asinxron generator.

        `yield` qilingan har bir string — SSE formatidagi BITTA xabar.
        SSE spetsifikatsiyasiga ko'ra har bir xabar albatta ikkita
        "\n" bilan tugashi kerak (`\n\n`) — bu brauzerga "xabar shu yerda
        tugadi" degan signal beradi (main.js'dagi buferni shu belgi
        bo'yicha bo'lib olamiz).
        """
        redis = aioredis.from_url(REDIS_URL)
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)

        try:
            # Ulanish ochilishi bilanoq — frontendga "men tayyorman" signali.
            # Bu shart emas, lekin frontendda "ulanish muvaffaqiyatli ochildi"
            # holatini ko'rsatish uchun qulay.
            yield "event: connected\ndata: {}\n\n"

            # `pubsub.listen()` — cheksiz asinxron sikl, Redis kanalga
            # PUBLISH bo'lgan HAR BIR xabarni shu yerda ushlab oladi.
            # Ulanish yopilmaguncha (brauzer tab yopilguncha yoki xato
            # chiqquncha) bu funksiya HECH QACHON o'z-o'zidan tugamaydi.
            async for message in pubsub.listen():
                if message["type"] != "message":
                    # pubsub.listen() dastlab "subscribe" turidagi xizmat
                    # xabarini ham yuboradi — bularni o'tkazib yuboramiz.
                    continue

                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode()

                # Redisdan kelgan xom JSON-string — o'zgarishsiz uzatiladi.
                # (Bu string ichida "task_id", "type", "result" kabi
                # maydonlar bor — frontend RCEvents shu maydonlar bo'yicha
                # to'g'ri joyga yo'naltiradi.)
                yield f"data: {data}\n\n"

        finally:
            # Brauzer ulanishni yopganda (tab yopilsa, sahifadan chiqilsa)
            # bu "finally" blok ishga tushadi — Redis obunasini va
            # ulanishni tozalab, resurs oqib ketishining (leak) oldini oladi.
            await pubsub.unsubscribe(channel)
            await redis.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            # Ba'zi proksi/serverlar (masalan nginx) javobni "buferlab"
            # keyin yuborishga harakat qiladi — bu esa SSE'ning "jonli"
            # bo'lish ma'nosini yo'qqa chiqaradi. Shu header shuni oldini
            # olishga yordam beradi (nginx X-Accel-Buffering: no).
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


