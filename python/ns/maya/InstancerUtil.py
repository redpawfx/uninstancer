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

# File: NSfnParticleInstancer.cpp
#
# Author: Nimble Studios Inc.
#
import sys

from maya.OpenMaya import *
from maya.OpenMayaFX import *

import ns.py as nspy
import ns.py.Errors

#import NSpy
#NSpy.nsReload( "NSerrors" )
#import NSmaya
#from NSerrors import *
#NSpy.nsReload( "NSmayaErrors" )
#from NSmayaErrors import *

#kPluginName = "blahBlah"



def particle( dpInstancer ):
	fInstancer = MFnInstancer( dpInstancer )
	# The particle system should be connected to the instancer's
	# inputPoints attribute.
	#
	aInputPoints = fInstancer.attribute("inputPoints")
	pInputPoints = MPlug( dpInstancer.node(), aInputPoints )

	sources = MPlugArray()
	pInputPoints.connectedTo( sources, True, False )

	if not sources.length() == 1:
		raise nspy.Errors.Error("No particle system associated with the instancer.")

	return sources[0].node(), sources[0].parent().logicalIndex()

def getInstance( dpInstancer, index ):
#
# Description:
#		Returns the index'th instanced object.
#
# WARNING:
#		If index'th element of inputHierarchyPlug does not exist
#		it will be created - so make sure that index is less
#		than the total number of instanced objects.
#
	pInputHier = inputHierarchyPlug( dpInstancer )
	plug = pInputHier.elementByLogicalIndex( index )

	sources = MPlugArray()
	plug.connectedTo( sources, True, False )

	if sources.length() == 0:
		return MObject.kNullObj

	return sources[0].node()

def inputHierarchyPlug( dpInstancer ):
	fInstancer = MFnInstancer( dpInstancer )
	aInputHierarchy = fInstancer.attribute("inputHierarchy")
	return MPlug( dpInstancer.node(), aInputHierarchy )


