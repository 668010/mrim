# -*- coding: utf-8 -*-

import config
import utils
import xmpp
import os
import threading
import traceback
import time

conf = config.Config()

class Profile:

	def __init__(self, jid, spool=conf.profile_dir):
		self.access = threading.Semaphore()
		self.spool = spool
		self.jid = xmpp.JID(jid).getStripped()
		self.file = os.path.join(self.spool, self.jid+'.xdb')

		self.register_ns = {
			'xmlns':xmpp.NS_REGISTER,
			'xdbns':xmpp.NS_REGISTER
		}
		self.roster_ns = {
			'xmlns':xmpp.NS_ROSTER,
			'xdbns':xmpp.NS_ROSTER
		}

		if os.path.exists(self.file):
			self.access.acquire()
			fd = open(self.file)
			self.xdb = xmpp.Node(node=fd.read())
			fd.close()
			self.access.release()
		else:
			self.xdb = xmpp.Node('xdb')
			register = xmpp.Node('query', attrs=self.register_ns)
			roster = xmpp.Node('query', attrs=self.roster_ns)
			self.xdb.setPayload([register,roster],add=0)

	def getRegister(self):
		for child in self.xdb.getChildren():
			if child.getAttr('xdbns') == xmpp.NS_REGISTER:
				return child

	def getRoster(self):
		for child in self.xdb.getChildren():
			if child.getAttr('xdbns') == xmpp.NS_ROSTER:
				return child

	def setUsername(self, username):
		register = self.getRegister()
		register.setTagData('username', username)
		self.flush()

	def setPassword(self, password):
		register = self.getRegister()
		register.setTagData('password', password)
		self.flush()

	def getUsername(self):
		register = self.getRegister()
		return register.getTagData('username')

	def getPassword(self):
		register = self.getRegister()
		return register.getTagData('password')

	def addItem(self, value):
		if value not in self.getRosterJids():
			roster = self.getRoster()
			item = xmpp.simplexml.Node('item', attrs={'jid':value})
			roster.setPayload([item],add=1)
		self.flush()

	def delItem(self, value):
		roster = self.getRoster()
		for child in roster.getChildren():
			if child.getAttr('jid') == value:
				roster.delChild(child)
		self.flush()

	def getItem(self, item):
		roster = self.getRoster()
		for child in roster.getChildren():
			if child.getAttr('jid')==item:
				return child

	def setItem(self, node):
		roster = self.getRoster()
		i = self.getItem(node.getAttr('jid'))
		if i:
			roster.delChild(i)
		roster.addChild(node=node)
		self.flush()

	def getRosterJids(self):
		roster = self.getRoster()
		items = [child.getAttr('jid') for child in roster.getChildren()]
		return items

	def getItems(self):
		roster = self.getRoster()
		return roster.getChildren()

	def getItemAttr(self, item, attr):
		i = self.getItem(item)
		ret_attr = ''
		if i:
			ret_attr = i.getAttr(attr) or ''
		return ret_attr

	def getItemName(self, item):
		return self.getItemAttr(item, 'name')

	def setItemAttr(self, item, attr, value):
		i = self.getItem(item)
		if i:
			i.setAttr(attr,value)
			self.flush()

	def delItemAttr(self, item, attr):
		i = self.getItem(item)
		if i:
			try:
				i.delAttr(attr)
			except KeyError:
				pass

	def setItemAttrs(self, item, attrs):
		i = self.getItem(item)
		if i:
			for attr,value in attrs.items():
				i.setAttr(attr,value)
			self.flush()

	def setItemGroup(self, item, group):
		i = self.getItem(item)
		if i:
			if group:
				i.setTagData('group', group)
			else:
				g = i.getTag('group')
				if g:
					i.delChild(node=g)
			self.flush()

	def getItemGroup(self, item):
		i = self.getItem(item)
		ret_g = ''
		if i:
			ret_g = i.getTagData('group') or ''
		return ret_g

	def setItemSub(self, item, subscription, ask=0):
		i = self.getItem(item)
		if i:
			self.setItemAttr(item, 'subscription', subscription)
			if subscription in ['from', 'to', 'both']:
				self.delItemAttr(item, 'ask')
			elif subscription=='none' and ask:
				self.setItemAttr(item, 'ask', 'subscribe')
			elif subscription=='none' and not ask:
				self.delItemAttr(item, 'ask')
			self.flush()

	def getItemSub(self, item):
		return self.getItemAttr(item,'subscription')

	def roster2dict(self):
		return [i.getAttrs() for i in self.getItems()]

	def remove(self):

		try:
			os.unlink(self.file)
			return True
		except OSError:
			return False

	def flush(self):
		self.access.acquire()
		try:
			s = self.xdb.__str__(fancy=1).encode('utf-8', 'replace')
		except:
			traceback.print_exc()
			return
		fd = open(self.file, 'w')
		fd.write('<?xml version="1.0" encoding="utf-8"?>\n')
		fd.write(s)
		fd.close()
		self.access.release()
