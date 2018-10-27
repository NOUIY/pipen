"""
The ssh runner
"""
import sys
from os import path, getcwd
from multiprocessing import Array
from subprocess import list2cmdline
from .runner import Runner
from ..utils import cmd, ps
from ..exception import RunnerSshError

MAX_SERVERS = 255

class RunnerSsh(Runner):
	"""
	The ssh runner
	"""
	LIVE_SERVERS = Array('i', [-1] * MAX_SERVERS)
	
	@staticmethod
	def isServerAlive(server, key = None):
		"""
		Check if an ssh server is alive
		"""
		cmdlist = ['ssh', server]
		if key: # pragma: no cover
			cmdlist.append('-i')
			cmdlist.append(key)
		cmdlist.append('-o')
		cmdlist.append('BatchMode=yes')
		cmdlist.append('-o')
		cmdlist.append('ConnectionAttempts=1')
		cmdlist.append('true')
		try:
			return cmd.run(cmdlist, timeout = 3).rc == 0
		except cmd.Timeout: # pragma: no cover
			return False

	def __init__ (self, job):
		"""
		Constructor
		@params:
			`job`:    The job object
		"""
		
		super(RunnerSsh, self).__init__(job)
		# construct an ssh cmd
		self.script = self.job.script + '.ssh'

		conf         = {}
		if 'sshRunner' in self.job.config.get('runnerOpts', {}):
			conf = self.job.config['runnerOpts']['sshRunner']
		
		servers    = conf.get('servers', [])
		keys       = conf.get('keys', [])
		checkAlive = conf.get('checkAlive', False)
		if not servers:
			raise RunnerSshError('No server found for ssh runner.')

		with RunnerSsh.LIVE_SERVERS.get_lock():
			if sum(RunnerSsh.LIVE_SERVERS) == -MAX_SERVERS:
				if checkAlive:
					liveservs = [
						i for i, server in enumerate(servers)
						if RunnerSsh.isServerAlive(server, keys[i] if keys else None)
					]
				else:
					liveservs = range(len(servers))
				for idx, servid in enumerate(liveservs):
					RunnerSsh.LIVE_SERVERS[idx] = servid
				
		if sum(RunnerSsh.LIVE_SERVERS) == -MAX_SERVERS:
			raise RunnerSshError('No server is alive.')

		sid    = RunnerSsh.LIVE_SERVERS[job.index % list(RunnerSsh.LIVE_SERVERS).index(-1)]
		server = servers[sid]
		key    = keys[sid] if keys else None

		self.cmd2run = "cd %s; %s" % (getcwd(), self.cmd2run)
		sshsrc       = [
			'#!/usr/bin/env bash',
			'# run on server: {}'.format(server),
			''
		]
		if 'preScript' in conf:
			sshsrc.append (conf['preScript'])
		
		sshsrc.append(self.cmd2run)
		
		if 'postScript' in conf:
			sshsrc.append (conf['postScript'])

		with open (self.script, 'w') as f:
			f.write ('\n'.join(sshsrc) + '\n')

		self.sshcmd = ['ssh', '-t', server]
		if key:
			self.sshcmd.append('-i')
			self.sshcmd.append(key)

	def submit(self):
		"""
		Submit the job
		@returns:
			The `utils.cmd.Cmd` instance if succeed 
			else a `Box` object with stderr as the exception and rc as 1
		"""
		cmdlist = ['ls', self.script]
		cmdlist = list2cmdline(cmdlist)
		c = cmd.run(self.sshcmd + [cmdlist])
		if c.rc != 0:
			c.stderr += 'Probably the server ({}) is not using the same file system as the local machine.\n'.format(self.sshcmd)
			return c
		
		# run self as a script
		submitter = path.join(path.realpath(path.dirname(__file__)), 'runner.py')
		cmdlist = [sys.executable, submitter, self.script]
		cmdlist = list2cmdline(cmdlist)
		c = cmd.run(self.sshcmd + [cmdlist], bg = True)
		c.rc = 0
		return c

	def kill(self):
		"""
		Kill the job
		"""
		cmdlist = 'ps -o pid,ppid'
		pidlist = cmd.run(self.sshcmd + [cmdlist]).stdout.splitlines()
		pidlist = [line.strip().split() for line in pidlist]
		pidlist = [pid for pid in pidlist if len(pid) == 2 and pid[0].isdigit() and pid[1].isdigit()]
		dchilds     = ps.child(self.job.pid, pidlist)
		allchildren = [str(self.job.pid)] + dchilds
		while dchilds: # pragma: no cover
			dchilds2 = sum([ps.child(p, pidlist) for p in dchilds], [])
			allchildren.extend(dchilds2)
			dchilds = dchilds2
		
		killcmd = ['kill', '-9'] + list(reversed(allchildren))
		killcmd = list2cmdline(killcmd)
		cmd.run(self.sshcmd + [killcmd])

	def isRunning(self):
		"""
		Tell if the job is alive
		@returns:
			`True` if it is else `False`
		"""
		if not self.job.pid:
			return False
		cmdlist = ['kill', '-0', str(self.job.pid)]
		cmdlist = list2cmdline(cmdlist)
		return cmd.run(self.sshcmd + [cmdlist]).rc == 0
