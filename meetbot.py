# -*- coding: utf-8 -*-
import datetime
import os
from jinja2 import Environment, FileSystemLoader

from tasbot.plugin import IPlugin
from tasbot.decorators import AdminOnly, MinArgs, NotSelf

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
		except Exception, e:
			self.logger.exception(e)
			raise VoteFailed(self.question,user, score)
			
	def result(self):
		return sum([score for user,score in self.votes.iteritems()])
	
class Main(IPlugin):
	def __init__(self,name,tasc):
		IPlugin.__init__(self,name,tasc)
		self._msg = []
		self._in_session = False
		self._logdir = tasc.main.config.get('meetbot', "logdir")
		try:
			os.mkdir(self._logdir)
		except:
			pass
		self._urlbase = tasc.main.config.get('meetbot', "urlbase")
		self._channel = tasc.main.config.get('meetbot', "channel")
		self._tops = []
		self.nick = tasc.main.config.get('tasbot', "nick")

	@AdminOnly
	@MinArgs(2)
	def cmd_saidprivate_goto(self,args,cmd):
		"""pm "!goto CHANNEL" to switch the bot to another channel"""
		self.say('bye')
		self.tasclient.leave(self._channel)
		self._channel = args[1]
		self.tasclient.join(self._channel)

	@NotSelf		
	@MinArgs(4)
	def cmd_said_top(self,args,cmd):
		"""start a new section in minutes with "!top title can have whitespace" """
		top = Top(' '.join(args[3:]),len(self._tops) + 1)
		self._tops.append(top)
		self._msg.append(top)

	@NotSelf
	def cmd_said_meetingend(self,args,cmd):
		"""write minutes to file and output url to it"""
		self._in_session = False
		self.say('meeting record ends')
		dt = str(self._begin).replace(' ', '_')
		fn = os.path.join(self._logdir, dt)
		env = Environment(loader=FileSystemLoader('.'))
		template = env.get_template('html.jinja')
		html_fn = fn + '.html'
		with open(html_fn, 'wb') as outfile:
			outfile.write( template.render(messages=self._msg,tops=self._tops,date=self._begin) )
		url = '%s/%s'%(self._urlbase,html_fn) 
		self.say(url)
		self._msg = []
		self._votes = []
		self._tops = []
		
	@NotSelf
	@MinArgs(3)
	def cmd_said(self,args,cmd):
		"""in an active session all SAID response not from myself are recorded"""
		if self._in_session:
			user = args[1]
			if user != self.nick:
				message = ' '.join(args[2:])
				self._msg.append(Message(user, message, 1))
			
	@NotSelf
	def cmd_said_meetingbegin(self,args,cmd):
		"""start a meeting session"""
		self._begin = datetime.datetime.now()
		self._in_session = True
		self._msg = []
		
	@NotSelf
	@MinArgs(4)
	def cmd_said_startvote(self,args,cmd):
		"""start a +- 1|0 vote with "!startvote QUESTION_TITLE" """
		vote = Vote(' '.join(args[3:]))
		self._current_vote = vote

	@NotSelf
	@MinArgs(4)
	def cmd_said_vote(self,args,cmd):
		"""give your vote to current question with "!vote +1","!vote 0" or "!vote -1" """ 
		user = args[1]
		score = args[3]
		try:
			self._current_vote.add_vote(user, score)
		except VoteFailed, fail:
			self.tasclient.saypm(user, str(fail))
		
	@NotSelf
	def cmd_said_endvote(self,args,cmd):
		"""end current voting and output result"""
		self._msg.append(self._current_vote)
		self.say('%s: %d'%(self._current_vote.question,self._current_vote.result()))
					
	def say(self,msg):
		self.tasclient.say(self._channel, msg)

		