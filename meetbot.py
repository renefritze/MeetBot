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
		self._user = u
		self._msg = m
		self._i = i

	def txt(self):
		return '%s: %s'%(self._user, self._msg)		
	
	def html(self):
		return '<span class="msg"><span class="user%d">%s</span>: %s</span>'%(self._i, self._user, self._msg)
	
class Top(object):
	def __init__(self,top,num):
		self.top = top
		self._num = num
		
	def html(self):
		return '<a name="top_%d"><h2>%s</h2></a>'%(self._num,self.top)
	
	def txt(self):
		return '----------------- %s --------------------'%self.top
	
class Vote(object):
	def __init__(self,question):
		self._question = question
		self._votes = {}
		
	def add_vote(self,user,score):
		try:
			def signum(x):
				return (x > 0) - (x < 0)
			score = int(score)
			self._votes[user] = signum(score) 
		except Exception, e:
			self.logger.exception(e)
			raise VoteFailed(self._question,user, score)
			
	def result(self):
		return sum([score for user,score in self._votes.iteritems()])
	
	def html(self):
		return '<span class="vote">%s - Result <span class="result">%d</span></span>'%(self._question,self.result())
	def txt(self):
		return '%s - Result %d\n'%(self._question,self.result())
	
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
		self.say('bye')
		self.tasclient.leave(self._channel)
		self._channel = args[1]
		self.tasclient.join(self._channel)

	@NotSelf		
	@MinArgs(3)
	def cmd_said_top(self,args,cmd):
		top = Top(' '.join(args[3:]),len(self._tops) + 1)
		self._tops.append(top)
		self._msg.append(top)

	@NotSelf
	def cmd_said_meetingend(self,args,cmd):
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
	@MinArgs(2)
	def cmd_said(self,args,cmd):
		if self._in_session:
			user = args[1]
			if user != self.nick:
				message = ' '.join(args[2:])
				self._msg.append(Message(user, message, 1))
			
	@NotSelf
	def cmd_said_meetingbegin(self,args,cmd):
		self._begin = datetime.datetime.now()
		self._in_session = True
		self._msg = []
		
	@NotSelf
	@MinArgs(3)
	def cmd_said_startvote(self,args,cmd):
		vote = Vote(' '.join(args[3:]))
		self._current_vote = vote

	@NotSelf
	@MinArgs(2)
	def cmd_said_vote(self,args,cmd):
		user = args[1]
		score = args[3]
		try:
			self._current_vote.add_vote(user, score)
		except VoteFailed, fail:
			self.tasclient.saypm(user, str(fail))
		
	@NotSelf
	def cmd_said_endvote(self,args,cmd):
		self._msg.append(self._current_vote)
		self.say(self._current_vote.txt())
					
	def say(self,msg):
		self.tasclient.say(self._channel, msg)

		