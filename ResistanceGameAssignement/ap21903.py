from player import Bot 
from game import State
import random
import inspect

# to run this python3 competition.py 1000 bots/beginners.py bots/neuralbot.py

import tensorflow as tf
from tensorflow import keras
model = keras.models.load_model('bots/loggerbot_classifier')
import numpy as np
import sys

from loggerbot import LoggerBot # this assumes our loggerbot was in a file called loggerbot.py

class Fatality(LoggerBot):

    def calc_player_probabilities_of_being_spy(self): 
        probabilities = {}
        vectors = []
        for p in self.game.players:
            # This list comprising the input vector must build in **exactly** the same way as
            # we built data to train our neural network - otherwise the neural network
            # is not bieng used to approximate the same function it's been trained to model.
            # That's why this class inherits from the class LoggerBot- so we can ensure that logic is replicated exactly.
            input_vector = [self.game.turn, self.game.tries, p.index, p.name, self.missions_been_on[p],
                            self.failed_missions_been_on[p],self.won_as_res[p],self.won_as_spy[p],
                            self.mission_success[p],self.missions_passed_as_spy[p]] + self.num_missions_voted_up_with_total_suspect_count[p] + \
                           self.num_missions_voted_down_with_total_suspect_count[p]
            input_vector = input_vector[
                           4:]  # remove the first 4 cosmetic details, as we did when training the neural network
            vectors.append(input_vector)
        vectors = np.stack(vectors, axis=0)
        output = model(vectors)  # run the neural network
        output_probabilities = tf.nn.softmax(output, axis=1) # The neural network didn't have a softmax on the final layer, so I'll add the softmax step here manually.
        for i in range(len(self.game.players)):
            probabilities[self.game.players[i]] = output_probabilities[i, 1]  # this [0,1] pulls off the first row (since there is only one row) and the second column (which corresponds to probability of being a spy; the first column is the probability of being not-spy)

        return probabilities  # This returns a dictionary of {player: spyProbability}
    
    """ Go through all teams in self.teams. If the player in a team is one of the players with highest failed missions add him to suspecios_players 
        remove yourself and suspecious_players from each team as you iterate through successful teams. If the t is not empty and the players in t are not already in team 
        add them to team. if length of team > = count-1 break and return the optimal team.
        param @count - number of players needed for the team"""
    def getOptimalTeam(self,count):
        team=[]
        failed_missions_player_has_been_on =[k for k, v in sorted(self.failed_missions_been_on.items(), key=lambda item:item[1])]
        suspecios_player = [s for s in failed_missions_player_has_been_on[-2:]]
        for t in self.teams: 
            if self in t:
                t.remove(self)
            if suspecios_player in t:
                t.remove(suspecios_player)
            if t:
                for player in t:
                    if player not in team:
                        team.append(player)
            if len(team) >= count-1:
                break
        return team
    
    """ Discard teams who are present in self.failedTeam"""
    def discard(self,team):
        for t in self.failedTeam:
            if set(t).issubset(set(team)):
                return True
        return False

    def select(self, players, count):
        self.say("Choose your Destiny!")
        team = [] # A lsit to store optimalTeam 
        if self.teams and self.game.turn>3: # Only use getOptimalTeam when you have played sufficient number of turns
            team=self.getOptimalTeam(count)
        
        spy_probs=self.calc_player_probabilities_of_being_spy()
        sorted_players_by_trustworthiness=[k for k, v in sorted(spy_probs.items(), key=lambda item: item[1])]
        
        for s in self.obviousSpies:
            if s in team:
                team.remove(s) # removes obvious spies
            if s in sorted_players_by_trustworthiness:
                sorted_players_by_trustworthiness.remove(s) # removes player from its position
                sorted_players_by_trustworthiness.append(s) # appends the player back at end of list so as not to go unde size

        if self.spy: # If spy always select yourself and randomly select 2 of the resistance members
            others = [p for p in players if p not in self.spies]
            result= [self] + random.sample(others, count-1)
        else:
            if len(team) > count-1: # if len(team) > count-1 result is [self] + team[:count-1]
                result = [self]+team[:count-1]
            elif len(team) == count-1: # if len(team) == count-1 , result is [self] + team[:count]
                result = [self] + team[:count]
            else: # Else go with the NN method
                if self in sorted_players_by_trustworthiness[:count]: 
                    result= sorted_players_by_trustworthiness[:count]
                else:
                    result= [self] + sorted_players_by_trustworthiness[:count-1]            
        return result

    def vote(self, team): 
        failed_missions_player_has_been_on =[k for k, v in sorted(self.failed_missions_been_on.items(), key=lambda item:item[1])]
        if self.spy:
            if self.game.tries == 5: #If tries == 5 vote down team and try to win the game 
                return False
            if self.downvotes>=2 and self in failed_missions_player_has_been_on[-2:]:
                return True # If downvotes >=3 you have already voted down team thrice in a row. Resistance would get suspecious 
            else:
                return len([p for p in team if p in self.spies]) > 0 # Vote down teams without spies

        if self.game.leader == self:
            return True # Always vote up the team you are leader of

        if not self.spy: # If not playing as spy, vote up team on 5th try
            if self.game.tries == 5: 
                return True
        # If you're not on the team and it's a team of 3!
        if len(self.game.team) == 3 and not self in self.game.team: 
            return False

        if self.discard(team): # If the team or a subscrript of team has been on a previous failed mission
            return False

        spy_probs=self.calc_player_probabilities_of_being_spy()
        sorted_players_by_trustworthiness=[k for k, v in sorted(spy_probs.items(), key=lambda item: item[1])]
        
        if not self.spy:
            # if a member of team is in both sorted_players_by_trustworthiness[-2:] and sorted_players_by_trustworthiness[-2:]
            #There is high chanvces he is a spy. Vote the team down.
            if[x for x in team if x in sorted_players_by_trustworthiness[-2:]] and [x for x in sorted_players_by_trustworthiness[-2:]]:
                return False
            if [s for s in self.obviousSpies]: # If a member of obviousSpies is in the team. vote the team down
                return False
        return True


    def sabotage(self):
        # the logic here is a bit boring and maybe could be improved.
        failed_missions_player_has_been_on =[k for k, v in sorted(self.failed_missions_been_on.items(), key=lambda item:item[1])]
        if self.game.turn==1: # Don't sabotage the first game
            return False
        if self.spy:
            if self.game.wins == 2: # Wins == 2, if you don't sabotage the mission resistance may win the game.
                return True
            if self.game.losses == 2: # losses == 2, sabotage the mission and win the game.
                self.say("Brutality!")
                return True
            # if you and another spy are in mission togather let the other spy sabotage the missiion if he is not one of the 2 players having highest  failed missions
            if self.otherSpy in self.game.team and self.otherSpy not in failed_missions_player_has_been_on[-2:] and self in failed_missions_player_has_been_on[-2:]:  
                return False 
            else: 
                return True
        else:
            return False

    """ @self.spies - used to get the spies if you are one.
        @self.failedTeam - List to store failed teams
        @self.otherSpy - used to get the other spy if you are a spy
        @self.downvotes - number of time you have voted down a tem this turn
        @self.teams - used to store teams that passed missions
        @obviousSpies - used store players who has voted down teams when tries==5 """
    def onGameRevealed(self, players, spies):
        self.say("Test your Might!")
        self.spies=spies
        self.failedTeam=[]
        self.otherSpy = [s for s in spies if s !=self]
        self.downvotes=0
        self.teams=[]
        self.obviousSpies=[]
        return super().onGameRevealed(players, spies)   


    def onMissionComplete(self, num_sabotages):
        if num_sabotages>0:
            self.failedTeam.append(self.game.team) # When mission is sabotaged add team to self.failedTeam
        self.downvotes=0 # Set downvotes to 0 once mission is completed and beforre next turn begins.
        if num_sabotages <=0: 
            self.teams.append(self.game.team) # When mission passes add the team to self.teams
        return super().onMissionComplete(num_sabotages)

    def onVoteComplete(self, votes):
        if votes[self.game.players.index(self)]:
            self.say("Get Over Here!")
            self.downvotes-=1 # Decrement self.downvotes by 1 when you have voted up a team
        else:
            self.say("Gotcha!")
            self.downvotes+=1 # Incremnt self.downvotes by 1 when you have voted down a team
        """ When tries==5, it is the last attempt to get a team. Highly probable that spies vote the team down 
            and try to win. Add players other than yourself and those already in self.obviousSpies to self.obviousSpies
            who have voted the team on 5th try. Hoping the majority didn't vote the team down if you are in resistance"""
        if self.game.tries>=5:
            for player in self.game.players:
                if not votes[self.game.players.index(player)]: 
                    if player not in self.obviousSpies and player != self:
                        self.obviousSpies.append(player)
                        self.say("Finish Him/Her!")
        return super().onVoteComplete(votes)
    # This function used to output log data to the log file. 
    # We don't need to log any data any more so let's override that function
    # and make it do nothing...
    
        
    def onGameComplete(self, win, spies):
        if win:
            if self.game.turn<=3: 
                self.say("FLAWLESS VICTORY!")
            else:
                self.say("FATALITY!")
        pass


