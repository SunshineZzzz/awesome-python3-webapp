# -*- coding: utf-8 -*-

__author__ = "Sunshine'Z"

'''
The subprocess module allows you to spawn new processes, connect to their input/output/error pipes, 
and obtain their return codes. This module intends to replace several older modules and functions:
os.system
os.spawn*
os.popen*
popen2.*
commands.*

watchdog
Python API and shell utilities to monitor file system events.
'''
import os, sys, time, subprocess

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

command = ['echo', 'ok']
process = None
py_version = sys.version_info

def log(s):
	print('[Monitor] %s' % s)

class MyFileSystemEventHandler(FileSystemEventHandler):
	def __init__(self, fn):
		'''
		继承FileSystemEventHandler
		:fn:重启函数
		:return:无
		'''
		super().__init__()
		self.restart  = fn

	def on_any_event(self, event):
		'''
		Catch-all event handler.
		:self: object self
		:event: The event object representing the file system event.
		:return:
		'''
		if event.src_path.endswith('.py'):
			# src_path - Source path of the file system object that triggered this event.
			log('Python source file changed: %s' % event.src_path)
			self.restart()

def start_process():
	global process, command
	log('Start process %s...' % ' '.join(command))
	process = subprocess.Popen(command, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)

def kill_process():
	global process
	if process:
		log('Kill process [%s]...' % process.pid)
		process.kill()
		process.wait()
		log('Process ended with code %s.' % process.returncode)
		process = None

def restart_process():
	kill_process()
	start_process()

def start_watch(path, callback):
	observe = Observer()
	observe.schedule(MyFileSystemEventHandler(restart_process), path, recursive=True)
	observe.start()
	log('Watching directory %s...' % path)
	start_process()
	try:
		while True:
			time.sleep(0.5)
	# KeyboardInterrupt - Raised when the user hits the interrupt key (normally Control-C or Delete).
	except KeyboardInterrupt:
		# Signals the thread to stop.
		observe.stop()
	# Wait until the thread terminates.
	observe.join()

if __name__ == '__main__':
	argv = sys.argv[1:]
	if not argv:
		print('Usage: ./pymonitor your-script.py')
		exit(0)
	if py_version <= (2, 7):
		print('Python version is greater than 2.7')
		exit(0)
	argv.insert(0, 'python')
	command = argv
	path = os.path.abspath('.')
	start_watch(path, None)