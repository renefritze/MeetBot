# -*- coding: utf-8 -*-

from tasbot.plugin import IPlugin


class Main(IPlugin):
	def __init__(self,name,tasc):
		IPlugin.__init__(self,name,tasc)
		self.chans = []
		self.admins = []

	def cmd_saidprivate(self,user,message):
		self.logger.info('dkjwop')
	def cmd_said_koko(self,user,message):
		self.logger.info('KOKO')

	def onload(self,tasc):
		self.app = tasc.main
		self.admins = self.app.config.get_optionlist('tasbot', "admins")

