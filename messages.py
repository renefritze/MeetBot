from tasbot.customlog import Log


class VoteFailed(Exception):
	def __init__(self, question, user, score):
		self.question = question
		self.user = user
		self.score = score
		
	def __str__(self):
		return 'Your vote for %s with %s failed. Make sure you vote by saying "!vote [+,-] [1,0]'%(self.question,self.score)
		
class Message(object):
	def __init__(self,u,m,i):
		self.user = u
		self.msg = m
		self.i = i
		#we need this marker to move the markup into the jinja template
		self.type = 'message'
	
class Top(object):
	def __init__(self,top,num):
		self.top = top
		self.num = num
		self.type = 'top'
			
class Vote(object):
	def __init__(self,question):
		self.question = question
		self.votes = {}
		self.type = 'vote'
		
	def add_vote(self,user,score):
		try:
			def signum(x):
				return (x > 0) - (x < 0)
			score = int(score)
			self.votes[user] = signum(score) 
		except Exception:
			Log.debug('Vote by %s failed'%user)
			raise VoteFailed(self.question,user, score)
			
	def result(self):
		return sum(self.votes.values())
	