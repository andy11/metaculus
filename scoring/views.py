from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
import scipy
import numpy as np

from questions.models import AggregateForecast
from questions.types import AggregationMethod
from users.models import User

from projects.models import Project
from projects.permissions import ObjectPermission
from projects.views import get_projects_qs, get_project_permission_for_user
from scoring.models import Leaderboard, LeaderboardEntry, Score
from scoring.serializers import (
    LeaderboardSerializer,
    LeaderboardEntrySerializer,
    ContributionSerializer,
)
from scoring.utils import get_contributions, hydrate_take


@api_view(["GET"])
@permission_classes([AllowAny])
def global_leaderboard(
    request: Request,
):
    # params
    start_time = request.GET.get("startTime", None)
    end_time = request.GET.get("endTime", None)
    leaderboard_type = request.GET.get("leaderboardType", None)
    # filtering
    leaderboards = Leaderboard.objects.filter(project_id=1)
    if start_time:
        leaderboards = leaderboards.filter(start_time=start_time)
    if end_time:
        leaderboards = leaderboards.filter(end_time=end_time)
    if leaderboard_type:
        leaderboards = leaderboards.filter(score_type=leaderboard_type)
    leaderboard_count = leaderboards.count()
    if leaderboard_count == 0:
        return Response(status=status.HTTP_404_NOT_FOUND)
    leaderboard = leaderboards.first()
    # serialize
    leaderboard_data = LeaderboardSerializer(leaderboard).data

    user = request.user
    entries = leaderboard.entries.select_related("user").order_by("rank")
    entries = entries.filter(rank__lte=max(3, entries.count() * 0.05))

    if not user.is_staff:
        entries = entries.filter(excluded=False)

    leaderboard_data["entries"] = LeaderboardEntrySerializer(entries, many=True).data
    # add user entry
    for entry in entries:
        if entry.user == user:
            leaderboard_data["userEntry"] = LeaderboardEntrySerializer(entry).data
            break
    return Response(leaderboard_data)


@api_view(["GET"])
@permission_classes([AllowAny])
def project_leaderboard(
    request: Request,
    project_id: int,
):
    # params
    leaderboard_type = request.GET.get("leaderboardType", None)
    leaderboard_name = request.GET.get("leaderboardName", None)

    projects = get_projects_qs(user=request.user)
    project: Project = get_object_or_404(projects, pk=project_id)
    # Check permissions
    permission = get_project_permission_for_user(project, user=request.user)
    ObjectPermission.can_view(permission, raise_exception=True)

    # filtering
    leaderboards = Leaderboard.objects.filter(project=project)
    if leaderboard_name:
        leaderboards = leaderboards.filter(name=leaderboard_name)
    if leaderboard_type:
        leaderboards = leaderboards.filter(score_type=leaderboard_type)

    # get leaderboard and project
    leaderboard_count = leaderboards.count()
    if leaderboard_count == 0:
        return Response(status=status.HTTP_404_NOT_FOUND)
    if leaderboard_count > 1:
        leaderboard = project.primary_leaderboard
        if not leaderboard:
            return Response(status=status.HTTP_404_NOT_FOUND)
    else:
        leaderboard = leaderboards.first()

    # serialize
    leaderboard_data = LeaderboardSerializer(leaderboard).data
    entries = leaderboard.entries.order_by("rank").select_related("user")
    user = request.user

    if not user.is_staff:
        entries = entries.filter(excluded=False)

    entries = hydrate_take(entries)  # NOTE: don't query after this as the
    # manual annotations will be lost
    leaderboard_data["entries"] = LeaderboardEntrySerializer(entries, many=True).data
    # add user entry
    for entry in entries:
        if entry.user == user:
            leaderboard_data["userEntry"] = LeaderboardEntrySerializer(entry).data
            break
    return Response(leaderboard_data)


@api_view(["GET"])
@permission_classes([AllowAny])
def user_medals(
    request: Request,
):
    user_id = request.GET.get("userId", None)
    if not user_id:
        return Response(status=status.HTTP_400_BAD_REQUEST)
    entries_with_medals = LeaderboardEntry.objects.filter(
        user_id=user_id, medal__isnull=False
    )
    entries = []
    for entry in entries_with_medals:
        entry_data = LeaderboardEntrySerializer(entry).data
        leaderboard = LeaderboardSerializer(entry.leaderboard).data
        total_entries = entry.leaderboard.entries.filter(excluded=False).count()
        entries.append({**entry_data, **leaderboard, "total_entries": total_entries})
    return Response(entries)


@api_view(["GET"])
@permission_classes([AllowAny])
def medal_contributions(
    request: Request,
):
    user_id = request.GET.get("userId", None)
    user = get_object_or_404(User, pk=user_id)
    project_id = request.GET.get("projectId", 1)

    projects = get_projects_qs(user=request.user)
    project: Project = get_object_or_404(projects, pk=project_id)
    # Check permissions
    permission = get_project_permission_for_user(project, user=request.user)
    ObjectPermission.can_view(permission, raise_exception=True)

    start_time = request.GET.get("startTime", None)
    end_time = request.GET.get("endTime", None)
    leaderboard_type = request.GET.get("leaderboardType", None)
    leaderboard_name = request.GET.get("leaderboardName", None)

    leaderboard = Leaderboard.objects.filter(project=project)
    if start_time:
        leaderboard = leaderboard.filter(start_time=start_time)
    if end_time:
        leaderboard = leaderboard.filter(end_time=end_time)
    if leaderboard_type:
        leaderboard = leaderboard.filter(score_type=leaderboard_type)
    if leaderboard_name:
        leaderboard = leaderboard.filter(name=leaderboard_name)

    if leaderboard.count() != 1:
        return Response(status=status.HTTP_404_NOT_FOUND)
    leaderboard = leaderboard.first()

    from datetime import datetime

    now = datetime.now()
    contributions = get_contributions(user, leaderboard)
    leaderboard_entry = leaderboard.entries.filter(user=user).first()

    return_data = {
        "leaderboard_entry": LeaderboardEntrySerializer(leaderboard_entry).data,
        "contributions": ContributionSerializer(contributions, many=True).data,
        "leaderboard": LeaderboardSerializer(leaderboard).data,
        "user_id": user_id,
    }
    return Response(return_data)


@api_view(["GET"])
@permission_classes([AllowAny])
def metaculus_track_record(
    request: Request,
):
    all_score_objs = Score.objects.filter(
        aggregation_method=AggregationMethod.RECENCY_WEIGHTED,
        score_type=Score.ScoreTypes.BASELINE,
    ).all()
    forecasts = (
        AggregateForecast.objects.filter(
            method=AggregationMethod.RECENCY_WEIGHTED,
            question__type="binary",
            question__resolution__in=["no", "yes"],
        )
        .prefetch_related("question")
        .all()
    )

    values = []
    weights = []
    resolutions = []
    questions_predicted = []
    scores = []
    question_score_map = {score.question_id: score for score in all_score_objs}

    for forecast in forecasts:
        question = forecast.question
        if question.id not in questions_predicted:
            questions_predicted.append(question.id)
            if score := question_score_map.get(question.id):
                scores.append(score.score)

        forecast_horizon_start = question.open_time.timestamp()
        actual_close_time = question.forecast_scoring_ends.timestamp()
        forecast_horizon_end = question.actual_close_time.timestamp()
        forecast_start = max(forecast_horizon_start, forecast.start_time.timestamp())
        if forecast.end_time:
            forecast_end = min(actual_close_time, forecast.end_time.timestamp())
        else:
            forecast_end = actual_close_time
        forecast_duration = forecast_end - forecast_start
        question_duration = forecast_horizon_end - forecast_horizon_start
        weight = forecast_duration / question_duration
        values.append(forecast.forecast_values[1])
        weights.append(weight)
        resolutions.append(int(question.resolution == "yes"))

    ser = {}
    calibration_curve = []
    for p_min, p_max in [(x / 20, x / 20 + 0.05) for x in range(20)]:
        res = []
        ws = []
        bin_center = p_min + 0.05
        for value, weight, resolution in zip(values, weights, resolutions):
            if p_min <= value < p_max:
                res.append(resolution)
                ws.append(weight)
        if res:
            user_middle_quartile = np.average(res, weights=ws)
        else:
            user_middle_quartile = None
        user_lower_quartile = scipy.stats.binom.ppf(
            0.05, max([len(res), 1]), bin_center
        ) / max([len(res), 1])
        user_upper_quartile = scipy.stats.binom.ppf(
            0.95, max([len(res), 1]), bin_center
        ) / max([len(res), 1])

        print(user_upper_quartile, user_lower_quartile, bin_center)
        calibration_curve.append(
            {
                "user_lower_quartile": user_lower_quartile,
                "user_middle_quartile": user_middle_quartile,
                "user_upper_quartile": user_upper_quartile,
                "perfect_calibration": bin_center,
            }
        )

    ser["calibration_curve"] = calibration_curve
    ser["score_histogram"] = [
        {"x_start": 0, "x_end": 0.2, "y": 0.7},
        {"x_start": 0.2, "x_end": 0.4, "y": 0.1},
        {"x_start": 0.4, "x_end": 0.6, "y": 0.05},
        {"x_start": 0.6, "x_end": 0.8, "y": 0.03},
        {"x_start": 0.8, "x_end": 1, "y": 0.02},
    ]

    ser["score_scatter_plot"] = []
    for score in all_score_objs:
        ser["score_scatter_plot"].append(
            {
                "score": score.score,
                "score_timestamp": score.created_at.timestamp(),
            }
        )
    ser["score_histogram"] = []
    bin_incr = 70
    for bin_start in range(-700, 700, bin_incr):
        bin_end = bin_start + bin_incr
        ser["score_histogram"].append(
            {
                "bin_start": bin_start,
                "bin_end": bin_end,
                "pct_scores": len([s for s in scores if s >= bin_start and s < bin_end])
                / len(scores),
            }
        )
    print(ser)
    return Response(ser)
