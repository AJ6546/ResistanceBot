from player import Bot 
from game import State
import random

class LoggerBot(Bot):

    # Loggerbot makes very simple playing strategy.
    # We're not really trying to win here, but just to observer the other players
    # without disturbing them too much....
    def select(self, players, count):
        return [self] + random.sample(self.others(), count - 1)

    def vote(self, team):
        return True

    def sabotage(self):
        return True
        
    def mission_total_suspect_count(self, team):
        total_suspect_count = 0
        for player in team:
            if player in self.failed_missions_been_on.keys():
                total_suspect_count += self.failed_missions_been_on[player]
        return min(total_suspect_count, 5)    
        
    def onVoteComplete(self, votes):
        suspectCount = self.mission_total_suspect_count(self.game.team)
        for player in self.game.players:
            if votes[self.game.players.index(player)]:
                self.num_missions_voted_up_with_total_suspect_count[player][suspectCount] += 1
            else:
                self.num_missions_voted_down_with_total_suspect_count[player][suspectCount] += 1
        """Callback once the whole team has voted.
        @param votes        Boolean votes for each player (ordered).
        """
         # TODO complete this function
    def onGameRevealed(self, players, spies):
        self.failed_missions_been_on = {}
        self.missions_been_on = {}
        self.num_missions_voted_up_with_total_suspect_count = {}
        self.num_missions_voted_down_with_total_suspect_count = {}
        #self.failed_missions_leadered = {}
        self.won_as_res={}
        self.won_as_spy={}
        self.mission_success={}
        self.missions_passed_as_spy={}
        for player in players:
            self.failed_missions_been_on[player] = 0
            self.missions_been_on[player] = 0
            self.num_missions_voted_up_with_total_suspect_count[player] = [0, 0, 0, 0, 0, 0]
            self.num_missions_voted_down_with_total_suspect_count[player] = [0, 0, 0, 0, 0, 0]
            #self.failed_missions_leadered[player] = 0
            self.won_as_res[player]=0
            self.won_as_spy[player]=0
            self.missions_passed_as_spy[player]=0
            self.mission_success[player]=0
        self.training_feature_vectors={}
        for p in players:
            self.training_feature_vectors[p]=[] # This is going to be a list of length-14 feature vectors for each player.
        """This function will be called to list all the players, and if you're
        a spy, the spies too -- including others and yourself.
        @param players  List of all players in the game including you.
        @param spies    List of players that are spies, or an empty list.
        """
        # TODO complete this function
    def onMissionComplete(self, num_sabotages):
        for player in self.game.team:
            self.missions_been_on[player] += 1
            if num_sabotages > 0:
                self.failed_missions_been_on[player] += 1
                """if player == self.game.leader:
                    self.failed_missions_leadered[player] += 1"""
            else:
                self.mission_success[player]+=1
        """Callback once the players have been chosen.
        @param num_sabotages    Integer how many times the mission was sabotaged.
        """
        # TODO complete this function
    def onGameComplete(self, win, spies):
        for player_number in range(len(self.game.players)):
            p=self.game.players[player_number]
            spy=p in spies # This will be a boolean
            if win:
                if p not in spies:
                    self.won_as_res[p] = 1
            else:
                if p in spies:
                    self.won_as_spy[p] = 1
            if p in spies:
                self.missions_passed_as_spy[p] =self.mission_success[p]
            self.training_feature_vectors[p].append([self.game.turn, self.game.tries, p.index, p.name, self.missions_been_on[p], 
            self.failed_missions_been_on[p],self.won_as_res[p],self.won_as_spy[p],
            self.mission_success[p],self.missions_passed_as_spy[p]]+self.num_missions_voted_up_with_total_suspect_count[p]+\
            self.num_missions_voted_down_with_total_suspect_count[p])
            feature_vectors=self.training_feature_vectors[p]  # These are our input features
            for v in feature_vectors:
                v.append(1 if spy else 0)  # append a 1 or 0 onto the end of our feature vector (for the label, i.e. spy or not spy)
                self.log.debug(','.join(map(str, v)) ) # converts all of elements of v into a csv list, and writes the full csv list to the log file

