from riotwatcher import LolWatcher, RiotWatcher, ApiError
from urllib.parse import quote
import requests

class RiotAgent:
    def __init__(self, api_key, riot_auth_url, riot_token_url, redirect_uri, server_region="NA1", match_region="AMERICAS"):
        self.__api_key = api_key

        self.__riot_auth_url = riot_auth_url
        self.__riot_token_url = riot_token_url
        self.__redirect_uri = redirect_uri
        
        self.__server_region = server_region
        self.__match_region = match_region
        
        self.__lol_watcher = None
        self.__riot_watcher = None

        self.__DEBUG = True
        print(f"[?][RIOT_AGENT][__init__] DATADRAGON AGENT DEBUG MODE: {self.__DEBUG}")

        return

    def __enter__(self):
        self.__lol_watcher = LolWatcher(self.__api_key)
        self.__riot_watcher = RiotWatcher(self.__api_key)
        if self.__DEBUG:
            print("[+][RIOT_AGENT][__enter__] Connected to Riot API")
        return

    # GETTERS
    def get_lol_watcher(self):
        return self.__lol_watcher
    
    def get_riot_watcher(self):
        return self.__riot_watcher


    # UTILITY FUNCTIONS
    def fetch_summoner_data(self, summoner_name):
        try:
            summoner = self.__riot_watcher().account.by_riot_id(self.__match_region, quote(summoner_name), self.__server_region)
            return summoner
        except ApiError as e:
            print(f"Error fetching summoner data: {e}")
            return None

    def fetch_match_data(self, game_id):
        try:
                match = self.__lol_watcher.match.by_id(self.__match_region, game_id)
                return match
        except ApiError as e:
                print(f"Error fetching match details: {e}")
                return None

# if __name__ == "__main__":
#         # Create a new instance of the Riot Agent
#         riot_agent = RiotAgent()

#         # Summoner name you want to lookup
#         summoner_name = quote('Sc00by')

#         my_account = riot_agent.get_riot_watcher().account.by_riot_id(MATCH_REGION, summoner_name, SERVER_REGION)
#         print(my_account)

#         me = riot_agent.get_lol_watcher().summoner.by_puuid(SERVER_REGION, my_account['puuid'])
#         print(me)

#         puuid = me['puuid']

#         # all objects are returned (by default) as a dict
#         # lets see if i got diamond yet (i probably didnt)
#         #my_ranked_stats = lol_watcher.league.by_summoner(my_region, me['id'])
#         #print(my_ranked_stats)

#         if puuid:
#                 print(f"PUUID for {summoner_name}: {puuid}")

#                 match_details = riot_agent.get_match_data("NA1_5211883203")
#                 print(match_details)

#                 # Fetch Details for Each Match
#                 if match_details:
#                         participants = match_details["info"]["participants"]
#                         for player in participants:
#                                 print(
#                                         f"Player: {player['riotIdGameName']}#{player['riotIdTagline']}, Gold Earned: {player['goldEarned']}"
#                                 )