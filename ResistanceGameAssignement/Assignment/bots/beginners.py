# All of the example bots in this file derive from the base Bot class.  See
# how this is implemented by looking at player.py.  The API is very well
# documented there.
from player import Bot 

# Each bot has access to the game state, stored in the self.game member
# variable.  See the State class in game.py for the full list of variables you
# have access to from your bot.
# 
# The examples below purposefully use only self.game to emphasize its
# importance.  Advanced bots tend to only use the game State class to decide!
from game import State


# Many bots will use random decisions to break ties between two equally valid
# options.  The simple bots below rely on randomness heavily, and expert bots
# tend to use other statistics and criteria (e.g. who is winning) to avoid ties
# altogether!
import random

import pandas as pd 

class Paranoid(Bot):
    """An AI bot that tends to vote everything down!"""

    def select(self, players, count):
        self.say("Picking myself and others I don't trust.")
        return [self] + random.sample(self.others(), count - 1)

    def vote(self, team): 
        self.say("I only vote for my own missions.")
        if not self.spy and (self in team or self.game.tries == 5):
            return True
        else:
            return bool(self == self.game.leader)

    def sabotage(self):
        self.log.debug("I always sabotage when I'm a spy.")
        if self.game.turn == 1 or int(len(self.game.team)) <= 2:
            return False
        else:
            return True 


class Hippie(Bot):
    """An AI bot that's OK with everything!"""

    def select(self, players, count):
        self.say("Picking some cool dudes to go with me!")
        return [self] + random.sample(self.others(), count - 1)

    def vote(self, team): 
        self.say("Everything is OK with me, man.")
        return True

    def sabotage(self):
        self.log.debug("Sabotaging is what spy dudes do, right?")
        return True


class RandomBot(Bot):
    """An AI bot that's perhaps never played before and doesn't understand the
    rules very well!"""

    def select(self, players, count):
        self.say("A completely random selection.")
        return random.sample(self.game.players, count)

    def vote(self, team): 
        self.say("A completely random vote.")
        return random.choice([True, False])

    def sabotage(self):
        self.log.debug("A completely random sabotage.")
        return random.choice([True, False])

    def announce(self):
        subset = random.sample(self.others(), random.randint(0, len(self.others())))
        return {p: random.random() for p in subset}


class Neighbor(Bot):
    """An AI that picks and votes for its neighbours and specifically does not
    use randomness in its decision-making."""

    @property
    def neighbors(self):
        n = self.game.players[self.index:] + self.game.players[0:self.index]
        return n

    def select(self, players, count):
        return self.neighbors[0:count]

    def vote(self, team):
        if self.game.tries == 5:
            return not self.spy
        n = self.neighbors[0:len(team)] + [self]
        for p in team:
            if not p in n: return False
        return True

    def sabotage(self):
        return len(self.game.team) == 2 or self.game.turn > 3


class Deceiver(Bot):
    """A tricky bot that's good at pretending being resistance as a spy."""

    def onGameRevealed(self, players, spies):
        self.spies = spies

    def select(self, players, count):
        return [self] + random.sample(self.others(), count - 1)

    def vote(self, team): 
        # Since a resistance would vote up the last mission...
        if self.game.tries == 5:
            return True
        # Spies select any mission with only one spy on it.
        if self.spy and len(self.game.team) == 2:
            return len([p for p in self.game.team if p in self.spies]) == 1
        # If I'm not on the team, and it's a team of 3...
        if len(self.game.team) == 3 and not self in self.game.team: 
            return False
        return True

    def sabotage(self):
        # Shoot down only missions with more than another person.
        return len(self.game.team) > 2


class RuleFollower(Bot):
    """Rule-based AI that does a pretty good job of capturing
    common sense play rules for THE RESISTANCE."""

    def onGameRevealed(self, players, spies):
        self.spies = spies

    def select(self, players, count):
        return [self] + random.sample(self.others(), count - 1)

    def vote(self, team): 
        # Both types of factions have constant behavior on the last try.
        if self.game.tries == 5:
            return not self.spy
        # Spies select any mission with one or more spies on it.
        if self.spy:
            return len([p for p in self.game.team if p in self.spies]) > 0
        # If I'm not on the team, and it's a team of 3...
        if len(self.game.team) == 3 and not self in self.game.team:
            return False
        return True

    def sabotage(self):
        return True


class Jammer(Bot):
    """An AI bot that plays simply as Resistance, but as a Spy plays against
    the common wisdom for synchronizing sabotages."""

    def onGameRevealed(self, players, spies):
        self.spies = spies

    def select(self, players, count):
        if not self.spies:
            return random.sample(self.game.players, count)
        else:
            # Purposefully go out of our way to pick the other spy so that we
            # can trick him with deceptive sabotaging!
            self.log.info("Picking the other spy to trick them!")    
            return list(self.spies) + random.sample(set(self.game.players) - set(self.spies), count-2)

    def vote(self, team): 
        return True

    def sabotage(self):
        spies = [s for s in self.game.team if s in self.spies]
        if len(spies) > 1:
            # Intermediate to advanced bots assume that sabotage is "controlled"
            # by the mission leader, so we go against this practice here.
            if self == self.game.leader:
                self.log.info("Not coordinating not sabotaging because I'm leader.")
                return False 

            # This is the opposite of the same practice, sabotage if the other
            # bot is expecting "control" the sabotage.
            if self.game.leader in spies:
                self.log.info("Not coordinating and sabotaging despite the other spy being leader.")
                return True
            spies.remove(self)

            # Often, intermeditae bots synchronize based on their global index
            # number.  Here we go against the standard pracitce and do it the
            # other way around!
            self.log.info("Coordinating according to the position around the table...")
            return self.index > spies[0].index
        return True

class CountingBot(Bot):

    def select(self, players, count):
        temp = [p for p, v in sorted(self.failed_missions_been_on.items(), key=lambda item: item[1])]
        temp.remove(self)
        return [self] + temp[:count-1]

    def vote(self, team):
        if self.spy:
            return False
        else:
            temp = [p for p, v in sorted(self.failed_missions_been_on.items(), key=lambda item: item[1])]
            two_most_suspected_players = temp[-2:]
            for p in team:
                if p in two_most_suspected_players:
                    return False
            return True

    def sabotage(self):
        return True

    def onGameRevealed(self, players, spies):
        self.failed_missions_been_on = {}
        for player in players:
            self.failed_missions_been_on[player] = 0

    def onMissionComplete(self, sabotaged):
        for player in self.game.team:
            if sabotaged:
                self.failed_missions_been_on[player] += 1

class TacticalCheater(Bot):
    """Has access to who the spies are even when playing resistance. Cheats tactically to avoid being cought as a cheater"""
    def select(self, players, count):
        temp = [p for p, v in sorted(self.failed_missions_been_on.items(), key=lambda item: item[1])]
        temp.remove(self)
        oneHighOneLow = [temp[0],temp[3]]
        self.most_suspected_player = temp[-1:]
        if not self.spy:
            if (self.game.wins <= self.game.losses): # Pick only ressistance menbers when you are loosing or in a tie to gain an advantage
                return [self] + self.ress[:count - 1]
            else:
                return [self] + oneHighOneLow[:count-1]
        else:
            return [self] + random.sample(self.others(), count - 1)


    def vote(self, team):
        shootdown = False
        if not self.spy and self.game.tries <3:
            for spy in self.spies:
                if spy in team:
                    shootdown = True
        return shootdown


    def sabotage(self):
        sabotage=False
        if not self.spy:
            for s in self.spies: # the spy will probably not sabotage as he know he is highly suspected so this will make the others confirm on the spy 
                if s in self.game.team and self.game.wins == 1 and self.game.losses <2 and s in self.most_suspected_player:
                    sabotage = True
        else:
            if self.otherSpy in self.game.team and self.game.wins < 2: # if self.game.wins==2 then sabotage and win the game else let the other spy sabotage 
                sabotage=False                                         # the mission or not sabotage the mission 
            else:
                sabotage=True                                       
        return sabotage    

    def onVoteComplete(self, votes):
        for player in self.game.players:
            pass
            #print(player," ", votes[self.game.players.index(player)])

    def onMissionComplete(self, sabotaged):
        for player in self.game.team:
            if sabotaged:
                self.failed_missions_been_on[player] += 1    
        
 
    def onGameRevealed(self, players, spies):
        self.spies = spies 
        self.ress =[]
        self.failed_missions_been_on = {}
        if self.spy:
           for s in self.spies:
               if s != self:
                   self.otherSpy=s
        for player in players:
            if player not in spies and self !=player:
                self.ress.append(player)
            self.failed_missions_been_on[player] = 0



        
        



