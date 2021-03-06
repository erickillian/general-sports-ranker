from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from ranker.core.models import (
    Event
)

from ranker.core.serializers import (
    EventSerializer,
)

from ranker.core.services import data

N_LAST_MATCHES = 10
N_PLAYERS = 5
N_DAYS_STATS_MAIN = 7
LB_CACHE_MINUTES = 1

class LeaderBoard(APIView):
    """
    Get data for leaderboard. Data is cached for LB_CACHE_MINUTES
    minutes. Set it to 0 if you dont need any caching
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    # @method_decorator(cache_page(LB_CACHE_MINUTES * 60, cache='leaderboard', key_prefix=''))
    def get(self, request):
        leaders = data.get_leaders(n_players=N_PLAYERS, rating_trend_days=N_DAYS_STATS_MAIN)
        # changes = data.get_changes_in_time(n_players=N_PLAYERS, n_days=N_DAYS_STATS_MAIN)
        maxes = data.get_maxes()
        totals = data.get_totals()

        return Response({
            'leaders': leaders,
            'weekly': [],
            'maxes': maxes,
            'totals': totals
        })
class EventList(APIView):
    """
    List of all events
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        events = Event.objects.all()
        serializer = EventSerializer(events, many=True)
        return Response(serializer.data)


class EventDetail(APIView):
    """
    Detailed event information
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, response, event_id):
        try:
            event_details = data.get_event_details(event_id=event_id)
            response = Response(event_details)
        except Event.DoesNotExist:
            response = Response(status=status.HTTP_404_NOT_FOUND)
        return response
