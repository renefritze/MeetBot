# -*- coding: utf-8 -*-
import datetime
import os
from jinja2 import Environment, FileSystemLoader

from tasbot.plugin import IPlugin
from tasbot.decorators import AdminOnly, MinArgs

class VoteFailed(Exception):
	def __init__(self, user, score):
		self.user = user
		self.score = score
		
class Message(object):
	def __init__(self,u,m,i):
		self._user = u
		self._msg = m
		self._i = i

	def txt(self):
		return '%s: \n'%(self._user, self._msg)		
	def html(self):
		return '<span class="msg"><span class="user%d">%s</span>%s</span>'%(self._i, self._user, self._msg)
	
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
		self._votes = []
		
	def add_vote(self,user,score):
		try:
			self._votes.append((user,int(score)))
		except:
			raise VoteFailed(user, score)
			
	def result(self):
		return sum([x[1] for x in self._votes])
	
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

	@AdminOnly
	@MinArgs(2)
	def cmd_saidprivate_goto(self,args,cmd):
		self.say('bye')
		self.tasclient.leave(self._channel)
		self._channel = args[1]
		self.tasclient.join(self._channel)
		
	def cmd_said_top(self,args,cmd):
		top = Top(' '.join(args[2:]))
		self._tops.append(top)
		self._msg.append(top)

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
		
	def cmd_said(self,args,cmd):
		if self._in_session:
			user = args[1]
			message = ' '.join(args[2:])
			self._msg.append(Message(user, message, 1))
			
	def cmd_said_meetingbegin(self,args,cmd):
		self._begin = datetime.datetime.now()
		self._in_session = True
		self._msg = []
			
	def say(self,msg):
		self.tasclient.say(self._channel, msg)

		