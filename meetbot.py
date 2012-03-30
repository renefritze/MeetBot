# -*- coding: utf-8 -*-
import datetime
import os
from jinja2 import Environment, FileSystemLoader

from tasbot.plugin import IPlugin
from tasbot.decorators import AdminOnly, MinArgs, NotSelf
from tasbot.colors import getColourPaletteCheat as getColourPalette

from messages import (Vote, VoteFailed, Message, Top)


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
		colors = getColourPalette(len(self.tasclient.channels[self._channel].users) + 1, 
								[(0.0,0,0.0),(1.0,1.0,1.0)])
		colors = [(int(r*256),int(g*256),int(b*256)) for (r,g,b) in colors]
		attending = self._everyone_but(self.tasclient.users[self.nick])
		with open(html_fn, 'wb') as outfile:
			outfile.write( template.render(messages=self._msg,tops=self._tops,date=self._begin, 
										colors=colors, attending=attending) )
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
		
	def _everyone_but(self, user):
		chan = self.tasclient.channels[self._channel]
		users = [self.nick,'ChanServ', user]
		return [s.username for s in chan.users if s.username not in users ]
	
	@NotSelf
	def cmd_said_ring(self,args,cmd):
		user = args[1]
		self.say('Ring ' + ', '.join( self._everyone_but(user) ) )
		for nick in self._everyone_but(user):
			self.tasclient.send_raw('RING %s'%nick)
					
	def say(self,msg):
		self.tasclient.say(self._channel, msg)

		