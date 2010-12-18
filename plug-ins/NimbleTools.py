# The MIT License
#	
# Copyright (c) 2009 James Piechota
#	
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.	

import os
import sys

from maya.OpenMayaMPx import *
import maya.mel as mel

# Initialize the script plug-in
def initializePlugin(oPlugin):
	fPlugin = MFnPlugin( oPlugin, "Nimble Studios Inc.", "1.2", "Any" );
	
	# Find the python source and add it to the pythonpath. This
	# assumes that this file (NimbleTools.py) lives in the 'plug-ins'
	# directory which is a sibling of the 'python' directory containing
	# the python source. This should be the case if the plug-in was
	# installed following the directions in the including INSTALL.txt
	# file.
	#
	installPath = "%s/.." % fPlugin.loadPath()
	pyPath = "%s/python" % installPath
	nsPath = "%s/ns" % pyPath
	if not os.path.isdir(pyPath) or not os.path.isdir(nsPath):
		sys.stderr.write( "Error loading plugin: NimbleTools python source was not found in %s\n" % pyPath )
		raise
	sys.path.append( pyPath )
	os.environ["NIMBLE_TOOLS_INSTALL"] = installPath
	
	import ns.maya.uninstancer.UninstancerCmd as UninstancerCmd
	
	try:
		fPlugin.registerCommand( UninstancerCmd.kPluginCmdName,
								 UninstancerCmd.cmdCreator,
								 UninstancerCmd.syntaxCreator )
		mel.eval("nsNimbleToolsCreateUI")
	except:
		sys.stderr.write( "Failed to register command: %s\n" % UninstancerCmd.kPluginCmdName )
		raise

# Uninitialize the script plug-in
def uninitializePlugin(oPlugin):
	fPlugin = MFnPlugin(oPlugin)
	try:
		fPlugin.deregisterCommand( UninstancerCmd.kPluginCmdName )
		mel.eval("nsNimbleToolsDeleteUI")
	except:
		sys.stderr.write( "Failed to unregister command: %s\n" % UninstancerCmd.kPluginCmdName )
		raise