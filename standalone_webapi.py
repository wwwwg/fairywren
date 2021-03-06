import eventlet
eventlet.monkey_patch()
import eventlet.backdoor
from eventlet import wsgi
from webapi import Webapi
from auth import *
from torrents import TorrentStore
from users import Users
import peers
import vanilla
import psycopg2
import sys
import json
import logging.config
import swarm

DEFAULT_LISTEN_IP ='127.0.0.1'
DEFAULT_LISTEN_PORT = 8081
DEFAULT_PATH_DEPTH = 1

if __name__ == '__main__':
	with open(sys.argv[1],'r') as fin:
		conf = json.load(fin)

	if 'logging' in conf['webapi']:
		logging.config.dictConfig(conf['webapi']['logging'])
		
	connPool = vanilla.buildConnectionPool(psycopg2,**conf['webapi']['postgresql'])
	
	authmgr = Auth(conf['salt'])
	authmgr.setConnectionPool(connPool)
	
	torrents = TorrentStore(conf['trackerUrl'])
	torrents.setConnectionPool(connPool)
		
	httpListenIp = conf['webapi'].get('ip',DEFAULT_LISTEN_IP)
	httpListenPort = conf['webapi'].get('port',DEFAULT_LISTEN_PORT)
	httpPathDepth = conf.get('pathDepth',DEFAULT_PATH_DEPTH)

	users = Users(conf['salt'])
	users.setConnectionPool(connPool)
	
	redisConnPool = vanilla.buildRedisConnectionPool(**conf['redis'])
	
	#Pass in zero and do not spawn the thread associated with the Peers
	#object. It is not needed in this process as it runs in the tracker
	#process.
	peerList = peers.Peers(redisConnPool,0)
	
	swarmConnPool = vanilla.buildConnectionPool(psycopg2,**conf['webapi']['postgresql'])
	swarm = swarm.Swarm()
	swarm.setConnectionPool(swarmConnPool)
	
	webapi = Webapi(swarm,peerList,users,authmgr,torrents,httpPathDepth,conf['webapi']['secure'])
	
	users.createRoles(webapi.getRoles())
	
	wsgi.server(eventlet.listen((httpListenIp, httpListenPort)), webapi)
