# -*- coding: utf-8 -*-
import datetime
import os
from jinja2 import Environment, FileSystemLoader
import cPickle as pickle
import fnmatch

from tasbot.plugin import IPlugin
from tasbot.decorators import AdminOnly, MinArgs, NotSelf
from tasbot.colors import getColourPaletteCheat as getColourPalette
from tasbot.colors import Color

from messages import (Vote, VoteFailed, Message, Top)

class Meeting(object):
	def __init__(self,msg_list,attending,begin,tops):
		self.msg_list = msg_list 
		self.attending = attending 
		self.begin = begin 
		self.tops = tops 

class Main(IPlugin):
	def __init__(self,name,tasc):
		IPlugin.__init__(self,name,tasc)
		self._msg = []
		self._in_session = False
		self._attending = set()
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
	def cmd_said_item(self,args,cmd):
		"""start a new item in minutes with "!item title can have whitespace" """
		top = Top(' '.join(args[3:]),len(self._tops) + 1)
		self._tops.append(top)
		self._msg.append(top)
		
	@NotSelf
	@MinArgs(3)
	def cmd_said(self,args,cmd):
		"""in an active session all SAID response not from myself are recorded"""
		if self._in_session:
			user = args[1]
			self._attending.add(user)
			if user != self.nick:
				message = ' '.join(args[2:])
				self._msg.append(Message(user, message, self._user_id(user)))
			
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
		users = [self.nick,'ChanServ','Nightwatch', user]
		return [s.username for s in chan.users if s.username not in users ]
	
	def _user_id(self, user):
		chan = self.tasclient.channels[self._channel]
		try:
			return [s.username for s in chan.users].index(user)
		except:
			return 0
	
	@NotSelf
	def cmd_said_ring(self,args,cmd):
		user = args[1]
		self.say('Ring ' + ', '.join( self._everyone_but(user) ) )
		for nick in self._everyone_but(user):
			self.tasclient.send_raw('RING %s'%nick)
					
	def say(self,msg):
		self.tasclient.say(self._channel, msg)

	@NotSelf
	def cmd_said_meetingend(self,args,cmd):
		"""write minutes to file and output url to it"""
		self._in_session = False
		self.say('meeting record ends')
		attending = [s for s in self._attending if s not in ('MeetBot','ChanServ','Nightwatch')]
		meet = Meeting(self._msg,attending,self._begin,self._tops)
		urls = self._output(meet) 
		pickle.dump(meet, open('meeting_%s.pickle'%self._begin, 'wb'))
		self.say('%s\n%s' % urls)
		self._msg = []
		self._votes = []
		self._tops = []

	def _output(self,meeting):
		dt = str(meeting.begin).replace(' ', '_')
		fn = os.path.join(self._logdir, dt)
		env = Environment(loader=FileSystemLoader('.'))
		template = env.get_template('html.jinja')
		html_fn = fn + '.html'
		bbcode_fn = fn + '.bbcode.txt'
		exclude = [Color((0,0,0)), Color((1,1,1)), Color((0.0,0.0,0.0)), Color((1.0,1.0,1.0))]
		colors = getColourPalette(len(meeting.attending) + 1, exclude)
		with open(html_fn, 'wb') as outfile:
			outfile.write( template.render(messages=meeting.msg_list, tops=meeting.tops, 
					date=meeting.begin, colors=colors, attending=meeting.attending) )
		template = env.get_template('bbcode.jinja')
		with open(bbcode_fn, 'wb') as outfile:
			outfile.write( template.render(messages=meeting.msg_list, tops=meeting.tops, 
					date=meeting.begin, colors=colors, attending=meeting.attending) )
		return ('%s/%s'%(self._urlbase,html_fn),'%s/%s'%(self._urlbase,bbcode_fn))

	@AdminOnly
	def cmd_said_redo(self, args, cmd):
		"""reload all pickled meetings and output them again"""
		cdir = '.'
		for fn in fnmatch.filter(os.listdir(cdir), 'meeting_*.pickle'):
			try:
				meet = pickle.load(open(fn,'rb'))
				urls = self._output(meet) 
				self.say('%s\n%s' % urls)
			except Exception,e:
				msg = 'Failed to pickle %s' % fn
				self.logger.error(msg)
				self.say(msg)
				self.logger.exception(e)
