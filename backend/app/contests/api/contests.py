from django_bolt import Router, Request
from django.db.models import Count, Q, Prefetch

from contests.models import (
    Contest,
    ContestPrize,
    ContestRegistration,
)


api = Router(tags=["Contest API"])


def get_optimized_contest_queryset():
    """
    Contest list uchun optimallashtirilgan queryset.

    Backend faqat kerakli database ma'lumotlarini oladi.
    UI/presentation logic frontendda bajariladi.
    """

    participant_filter = Q(
        registrations__status__in=[
            ContestRegistration.Status.IN_PROGRESS,
            ContestRegistration.Status.COMPLETED,
        ]
    )

    prize_queryset = (
        ContestPrize.objects
        .only(
            "contest_id",
            "rank_target",
            "title",
            "description",
        )
        .order_by("rank_target")
    )

    return (
        Contest.objects
        .filter(is_active=True)

        # ForeignKey
        .select_related("intro_video")

        # Faqat kerakli Contest fieldlar
        .only(
            "id",
            "title",
            "slug",
            "description",
            "visibility",
            "contest_type",
            "format",
            "start_time",
            "end_time",
            "registration_deadline",
            "duration_minutes",
            "allow_practice",
            "penalty_minutes_per_wrong",
            "intro_video",
            "is_active",
        )

        # Ishtirokchilar soni
        .annotate(
            participant_count=Count(
                "registrations",
                filter=participant_filter,
                distinct=True,
            )
        )

        # Prize'larni alohida query bilan olish
        .prefetch_related(
            Prefetch(
                "prizes",
                queryset=prize_queryset,
            )
        )

        # Eng yaqin contestlar birinchi
        .order_by("start_time")
    )


def serialize_contest(contest: Contest) -> dict:
    """
    Contest modelini API response'ga aylantiradi.

    Bu yerda presentation logic qilinmaydi.
    """

    return {
        "id": contest.id,
        "title": contest.title,
        "slug": contest.slug,
        "description": contest.description,

        "visibility": contest.visibility,
        "contest_type": contest.contest_type,
        "format": contest.format,

        "start_time": contest.start_time.isoformat(),
        "end_time": contest.end_time.isoformat(),

        "registration_deadline": (
            contest.registration_deadline.isoformat()
            if contest.registration_deadline
            else None
        ),

        "duration_minutes": contest.duration_minutes,

        "allow_practice": contest.allow_practice,

        "penalty_minutes_per_wrong": (
            contest.penalty_minutes_per_wrong
        ),

        "participant_count": (
            contest.participant_count
        ),

        "intro_video": (
            {
                "id": str(contest.intro_video.id),
                "hls_url": contest.intro_video.hls_url,
                "thumbnail": (
                    contest.intro_video.thumbnail.url
                    if contest.intro_video.thumbnail
                    else None
                ),
                "duration": contest.intro_video.duration,
            }
            if contest.intro_video
            else None
        ),

        "prizes": [
            {
                "rank": prize.rank_target,
                "title": prize.title,
                "description": prize.description,
            }
            for prize in contest.prizes.all()
        ],
    }


@api.get("/")
async def contest_list(request: Request):
    """
    Faol contestlar ro'yxati.
    """
    headers = request.get("headers", {})
    print("Header", headers)
    queryset = get_optimized_contest_queryset()

    return [
        serialize_contest(contest)
        async for contest in queryset
    ]