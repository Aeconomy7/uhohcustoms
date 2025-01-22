from riotwatcher import LolWatcher, RiotWatcher, ApiError
from urllib.parse import quote
import requests

# GLOBALS
# RIOT API CONFIGURATIONS
RIOT_API_KEY		= "RGAPI-fd909656-cc3d-4f8d-9e84-01b6f090e4b6"
RIOT_CLIENT_ID		= "PLACEHOLDER"
RIOT_CLIENT_SECRET	= "PLACEHOLDER"
RIOT_AUTH_URL		= "https://auth.riotgames.com/authorize"
RIOT_TOKEN_URL		= "https://auth.riotgames.com/token"
REDIRECT_URI		= "https://uhohcustoms.lol/callback"
MATCH_REGION		= "AMERICAS"
SERVER_REGION		= "NA1"

class RiotAgent:
    def __init__(self, api_key):
        self.__server_region = SERVER_REGION
        self.__match_region = MATCH_REGION
        self.__api_key = api_key

        # Init Watcher
        self.__lol_watcher = LolWatcher(self.__api_key)
        self.__riot_watcher = RiotWatcher(self.__api_key)
        print(f"[+][RIOT_AGENT][__init__] Initialized Riot Agent")

    # GETTERS
    def get_lol_watcher(self):
        return self.__lol_watcher
    
    def get_riot_watcher(self):
        return self.__riot_watcher

    def get_match_data(self, game_id):
        try:
                match = self.__lol_watcher.match.by_id(self.__server_region, game_id)
                return match
        except ApiError as e:
                print(f"Error fetching match details: {e}")
                return None

if __name__ == "__main__":
        # Create a new instance of the Riot Agent
        riot_agent = RiotAgent(RIOT_API_KEY)

        # Summoner name you want to lookup
        summoner_name = quote('Sc00by')

        my_account = riot_agent.get_riot_watcher().account.by_riot_id(MATCH_REGION, summoner_name, SERVER_REGION)
        print(my_account)

        me = riot_agent.get_lol_watcher().summoner.by_puuid(SERVER_REGION, my_account['puuid'])
        print(me)

        puuid = me['puuid']

        # all objects are returned (by default) as a dict
        # lets see if i got diamond yet (i probably didnt)
        #my_ranked_stats = lol_watcher.league.by_summoner(my_region, me['id'])
        #print(my_ranked_stats)

        if puuid:
                print(f"PUUID for {summoner_name}: {puuid}")

                match_details = riot_agent.get_match_data("NA1_5211883203")
                print(match_details)

                # Fetch Details for Each Match
                if match_details:
                        participants = match_details["info"]["participants"]
                        for player in participants:
                                print(
                                        f"Player: {player['riotIdGameName']}#{player['riotIdTagline']}, Gold Earned: {player['goldEarned']}"
                                )