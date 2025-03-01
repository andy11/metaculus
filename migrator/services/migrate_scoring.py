from questions.models import Question
from scoring.utils import score_question
from scoring.models import Score


def score_questions(qty: int | None = None):
    questions = Question.objects.filter(
        resolution__isnull=False,
    ).exclude(
        resolution__in=["ambiguous", "annulled"],
    )
    if qty:
        questions = questions.order_by("?")[:qty]
    c = len(questions)
    question: Question
    for i, question in enumerate(questions, 1):
        if question.resolution and not question.forecast_scoring_ends:
            print(
                question.forecast_scoring_ends,
                question.resolution,
                question.get_post().title,
                question.get_post().id,
            )
            print("Resolved q with no resolved time")
            exit()
        try:
            score_question(
                question,
                question.resolution,
                # TODO: add spot_forecast_time
                score_types=[Score.ScoreTypes.PEER, Score.ScoreTypes.BASELINE],
            )
            print("scored question", i, "/", c, "ID:", question.id, end="\r")
        except Exception as e:
            if "ambiguous or annulled" in str(e):
                pass
            else:
                raise e
