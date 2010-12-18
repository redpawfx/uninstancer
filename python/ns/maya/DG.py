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

from maya.OpenMaya import *

import ns.py as nspy
import ns.py.Const

import ns.maya as nsm
import ns.maya.Errors


def getPlug( node = MObject(),
			 attr = MObject(),
			 nodeName = "",
			 attrName = "",
			 index = nspy.Const.kInvalidIndex,
			 wantNetworkedPlug = False ):
	if ( not node.isNull() and not attr.isNull() ):
		return _plugFromNodeAndAttr( node, attr, index, wantNetworkedPlug )
	elif ( not node.isNull() and attrName ):
		return _plugFromNodeAndAttrName( node, attrName, index, wantNetworkedPlug )
	elif ( nodeName and attrName ):
		return _plugFromNodeNameAndAttrName( nodeName, attrName, index, wantNetworkedPlug )
	else:
		raise nsm.Errors.BadArgumentError("Invalid arguments.")
	
def _plugFromNodeAndAttr( node, attr, index, wantNetworkedPlug ):
#
# Get a plug given a node, attribute, and multi index.
#
	fNode = MFnDependencyNode( node )
	plug = fNode.findPlug( attr, wantNetworkedPlug )
	_findMultiIndex( plug, index )
	return plug;	

def _plugFromNodeAndAttrName( node, attrName, index, wantNetworkedPlug ):
#
# Get a plug given a node, attribute name, and multi index.
#
	fNode = MFnDependencyNode( node )
	plug = fNode.findPlug( attrName, wantNetworkedPlug )
	_findMultiIndex( plug, index )
	return plug

def _plugFromNodeNameAndAttrName( nodeName, attrName, index, wantNetworkedPlug ):
#
# Get a plug given a node name, attribute name, and multi index.
#
	list = MSelectionList()
	MGlobal.getSelectionListByName( nodeName, list )
	if 0 == list.length():
		raise nsm.Errors.MayaError( "Node " + nodeName + " does not exist." )

	oNode = MObject()
	list.getDependNode( 0, oNode )
	return _plugFromNodeAndAttrName( oNode, attrName, index, wantNetworkedPlug )


def _findMultiIndex( plug, index ):
#
# If the index is valid and plug is an array-parent, find the
# appropriate array element.
#
	if nspy.Const.kInvalidIndex != index:
		if plug.isArray():
			plug = plug.elementByLogicalIndex( index )
		else:
			raise nspy.Errors.BadArgumentError( "%s is not an array attribute - index %d can not be retrieved." % (plug.name(), index))
