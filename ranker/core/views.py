from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.utils import timezone
from django.forms.models import model_to_dict
from django.db.models import Avg
from django.db.models.expressions import Window
from django.db.models.functions import RowNumber
from django.db.models import F


from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets

from ranker.core.models import (
    Player, Event, PlayerRating, Wordle, ActiveWordle,
)
from ranker.core.serializers import (
    PlayerSerializer,
    PlayerWordleGuessesSerializer,
    PlayerWordleTimeSerializer,
    EventSerializer,
    RatingHistorySerializer,
    MatchHistorySerializer,
    ActiveWordleSerializer,
    WordleGuessSerializer,
    WordleSerializer
)
from ranker.core.services import data

import json, os, random
from ranker.settings.dev import BASE_DIR

import datetime


from ranker.core.constants.wordle import WORDLE_MAX_LENGTH, WORDLE_NUM_GUESSES

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

    @method_decorator(cache_page(LB_CACHE_MINUTES * 60, cache='leaderboard', key_prefix=''))
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


class PlayerList(APIView):
    """
    List of all players
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        players = Player.objects.all()
        serializer = PlayerSerializer(players, many=True)
        return Response(serializer.data)


class PlayerDetail(APIView):
    """
    Player data
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, player_id):
        try:
            player = Player.objects.get(pk=player_id)
            serializer = PlayerSerializer(player)
            response = Response(serializer.data)
        except Player.DoesNotExist:
            response = Response(status=status.HTTP_404_NOT_FOUND)
        return response


class PlayerRatingHistory(APIView):
    """
    Player history rating for charts
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, player_id):
        try:
            player = PlayerRating.objects.get(pk=player_id)
            serializer = RatingHistorySerializer(player.rating_history_days, many=True)
            return Response(serializer.data)
        except PlayerRating.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class PlayerMatchHistory(APIView):
    """
    Player match history
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, player_id):
        summary = data.get_last_matches(player_id=player_id, n_matches=N_LAST_MATCHES)
        serializer = MatchHistorySerializer(summary, many=True)
        return Response(serializer.data)


class PlayerStats(APIView):
    """
    Simple player statistics
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, player_id):
        try:
            stats = data.get_player_stats(player_id=player_id)
            return Response(stats)
        except PlayerRating.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class PlayerWordles(APIView):
    def get(self, request, player_id):
        try:
            queryset = Wordle.objects.filter(player=player_id).order_by('date')
            serializer = WordleSerializer(queryset, many=True)
            return Response(serializer.data)
        except PlayerRating.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)



class WordleStatus(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            wordle = Wordle.objects.get(player=request.user, date=timezone.now().date())
            active_wordle = ActiveWordle.objects.get(player=request.user)
        except Wordle.DoesNotExist:
            try:
                active_wordle = ActiveWordle.objects.get(player=request.user)
                if active_wordle.date != timezone.now().date():
                    # If the user never completes their wordle for the day
                    active_wordle.delete()
                    active_wordle = ActiveWordle(word="?", guess_history="")
            except ActiveWordle.DoesNotExist:
                active_wordle = ActiveWordle(word="?", guess_history="")
        except ActiveWordle.DoesNotExist:
            # this should never happen, if it does there is a problem
            guess_history = "?"*WORDLE_MAX_LENGTH*(wordle.guesses-1)+wordle.word
            active_wordle = ActiveWordle(word=wordle.word, guess_history=guess_history)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = ActiveWordleSerializer(active_wordle)
        return Response(serializer.data)

    
wordle_target_words = json.load(open(os.path.join(BASE_DIR, 'ranker/core/constants/targetWords.json')))

class WordleGuess(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = WordleGuessSerializer

    def post(self, request):
        active_wordles = ActiveWordle.objects.filter(player=request.user, start_time__date=timezone.now().date())
        daily_wordles = Wordle.objects.filter(player=request.user, date=timezone.now().date())

        if len(active_wordles) == 0 and len(daily_wordles) == 0:
            guess_serializer = WordleGuessSerializer(data=request.data)
            if guess_serializer.is_valid():
                # Deletes the old active wordle for the player if one exists
                active_wordles = ActiveWordle.objects.filter(player=request.user).delete()

                word = random.choice(wordle_target_words)
                active_wordle = ActiveWordle.objects.create(
                    player=request.user, 
                    guess_history=request.data['guess'], 
                    word=word
                )
                serializer = ActiveWordleSerializer(active_wordle)
                return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
            else:
                return Response(status=status.HTTP_400_BAD_REQUEST)

        # If an active wordle for the user exists and they have no wordles
        # on record for that day validate their guess 
        elif len(active_wordles) == 1 and len(daily_wordles) == 0:
            active_wordle = active_wordles[0]
            if active_wordle.guesses >= WORDLE_NUM_GUESSES:
                return Response(status=status.HTTP_400_BAD_REQUEST)

            guess_serializer = WordleGuessSerializer(data=request.data)
            if guess_serializer.is_valid():
                active_wordle.guess_history += request.data['guess']
                active_wordle.save()
                serializer = ActiveWordleSerializer(active_wordle)
                
                if active_wordle.guesses == WORDLE_NUM_GUESSES or active_wordle.solved:
                    Wordle.objects.create(
                        player=request.user, 
                        word=active_wordle.word,
                        guesses=active_wordle.guesses,
                        date=active_wordle.date,
                        time=timezone.now()-active_wordle.start_time,
                        fail=not active_wordle.solved
                    )
                return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
            
            else:
                return Response(status=status.HTTP_400_BAD_REQUEST)
        elif len(active_wordles) == 1 and len(daily_wordles) == 1:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        elif len(active_wordles) > 1:
            active_wordles[0].delete()
            return Response(status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)

# class WordleDetail(APIView):
#     authentication_classes = [SessionAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get(self, request, pk):
#         pass

class WordleViewSet(viewsets.ViewSet):
    """
    A simple ViewSet for listing or retrieving Wordles.
    """
    def list(self, request):
        queryset = Wordle.objects.all()
        serializer = WordleSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        queryset = Wordle.objects.all()
        daily_wordle = get_object_or_404(queryset, pk=pk)
        serializer = WordleSerializer(daily_wordle)
        return Response(serializer.data)


class WordlesToday(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = WordleSerializer

    def get(self, request):
        queryset = Wordle.objects.filter(
            date=timezone.now().date()
        ).order_by('fail', 'guesses', 'time').annotate(
            rank=Window(
                expression=RowNumber(),
                order_by=['fail', 'guesses', 'time']
            )
        )
        serializer = WordleSerializer(queryset, many=True)
        return Response(serializer.data)


class WordleLeaders(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = []
    serializer_class = WordleSerializer

    def get(self, request):

        players = Player.objects.annotate(avg_guesses=Avg('wordle__guesses'), avg_time=Avg('wordle__time'))
        
        if len(players) > 0:
            players_best_avg_time = players.order_by('avg_time')[:5]
            players_best_avg_guesses = players.order_by('avg_guesses')[:5]
            print(players_best_avg_time, flush=True)
            print(players_best_avg_guesses, flush=True)


        return Response(status=status.HTTP_200_OK)

class WordleLeadersTime(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = []
    serializer_class = PlayerWordleTimeSerializer

    def get(self, request):

        players = Player.objects.annotate(avg_time=Avg('wordle__time'))

        queryset = players.order_by('avg_time')[:5]
        print(queryset, flush=True)
        
        serializer = PlayerWordleTimeSerializer(queryset, many=True)
        print(queryset, flush=True)

        return Response(serializer.data)


class WordleLeadersGuesses(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = []
    serializer_class = PlayerWordleGuessesSerializer

    def get(self, request):

        queryset = Player.objects.annotate(avg_guesses=Avg('wordle__guesses')).order_by('avg_guesses')[:5]
        
        serializer = PlayerWordleGuessesSerializer(queryset, many=True)
        return Response(serializer.data)


class WordleWallOfShame(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = WordleSerializer

    def get(self, request):
        queryset = Wordle.objects.filter(fail=True)
        serializer = WordleSerializer(queryset, many=True)
        return Response(serializer.data)

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
