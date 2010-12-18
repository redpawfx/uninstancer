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


#
#	NSuninstancerCmd.cpp
#	
#
#
# Limitations/Extensions:
# 1. If instanced shape is animated, uninstanced ones will not
#	  be.
# 2. If the shape that is instanced onto the particle system is
#	  also instanced in the DAG (i.e. it has multiple DAG paths
#	  leading to it), undo/redo will not work properly. This is
#	  a bug with the Maya API and has been logged.
#
# FIXED:
# 5. Baking animation when frame cycling or per object indicing
#	  is used will not preserve the cycling. I should back the
#	  the geometry to blendShapes (from MikeRhone on CGTalk:
#	  http:#forums.cgsociety.org/showthread.php?p=3674406#post3674406)
#
# TO TEST:
# 1. What happens when instanced objects are translated oddly, or the
#	  topology doesn't match? (When baking animation)
#
# Notes:
# 
# Duplicates will be parented to world. This is to avoid problems when
# a node in the middle of a dag hierarchy was instanced to the particle
# system. In that situation the transformations of the nodes above
# the instanced shape will affect the original object but *not* the
# particle instances. If the duplicates are parented to the same node
# as the original then they will not match the particle instances.
#
# TODO:
# 1. Check instancer pivot - createInstancerPivot
# 2. Make sure everything is cleaned up if thecommand fails in the middle
#
#
# Notes:
# Select either an instancer, a particle system, or individual particles
# If an instancer is selected, all particles in the associated particle
# system are acted on.
# If a particle system is selected and it only has one instancer, then
# that instancer/system combination is acted on.
# If a particle system is selected and it has more than one instancer
# then the desired instancer has to be provided using the -instancer
# flag.
# Individual particles are handled the same as the particle system except
# only the selected particles are acted on.
#
# TODO:
#	1. add useful error messages back when a method call throws an exception
#	2. Use x or y syntax to assign default values ageAttr = getAttr() or "age"


import sys

from maya.OpenMaya import *
from maya.OpenMayaAnim import *
from maya.OpenMayaFX import *
import maya.OpenMayaMPx as OpenMayaMPx
import maya.cmds

import ns.py as nspy
import ns.py.Errors
import ns.py.Const
import ns.py.Timer
import ns.maya as nsm
import ns.maya.Errors
import ns.maya.Utils
import ns.maya.InstancerUtil
import ns.maya.ParticleUtil
import ns.maya.MayaModifier
import ns.maya.Progress
from ns.maya.uninstancer.Geometry import *
from ns.maya.uninstancer.Instancer import *


kPluginCmdName = "nsUninstancer"


kInstancerFlag 		= "ins"
kInstancerFlagLong 	= "instancer"
kCopyAsInstanceFlag 	= "cai"
kCopyAsInstanceFlagLong = "copyAsInstance"
kStartFrameFlag 	= "sf"
kStartFrameFlagLong 	= "startFrame"
kEndFrameFlag 		= "ef"
kEndFrameFlagLong 	= "endFrame"
kFrameStepFlag 		= "fs"
kFrameStepFlagLong 	= "frameStep"
kBakeTypeFlag 		= "bt"
kBakeTypeFlagLong 	= "bakeType"

# NSuninstancerCmd enums
# TODO: try moving these class definitions into class NSuninstancerCmd?
# TODO: try prefacing the class name with _ or _
class eBake:
	geometry, curves, animation, blendShapes, numValues = range(5)

# command
class UninstancerCmd(OpenMayaMPx.MPxCommand):
	
	def __init__(self):
		OpenMayaMPx.MPxCommand.__init__(self)
 
		self._dpInstancer = MDagPath()
		self._dpParticle = MDagPath()
		self._copyAsInstance = False
		self._bakeType = eBake.geometry
		self._startFrame = -1
		self._endFrame = -1
		self._frameStep = 1
		self._particleIdOffset = 0
		self._hasBeenUndone = False
		self._targetParticleIds = []
		self._animData = []
		self._modifier = MDagModifier()
		self._mayaModifier = nsm.MayaModifier.MayaModifier()
		self._uninstances = {}
		
	# Creator
		
	def isUndoable( self ):
		return True
		
	def doIt( self, argList ):
		self.clearResult()
		self.parseArg( argList )
		
		nsm.Progress.advanceProgress( 1 )
		
		assert self._endFrame >= self._startFrame


		
		try:
			nsm.Progress.setTitle("Run up")
			nsm.ParticleUtil.runUpTo( self._dpParticle, self._startFrame )
			nsm.Progress.advanceProgress( 1 )
			
			fInstancer = MFnInstancer( self._dpInstancer )
			idMapper = nsm.ParticleUtil.IdMapper()
			
			for curFrame in range( self._startFrame, self._endFrame + 1 ):
				curTime = MTime( curFrame, MTime.uiUnit() )
				MAnimControl.setCurrentTime( curTime )
				
				# Only bake geometry/animation every frameStep frames.
				# But still make sure to call setCurrentTime so any
				# particle systems that depend on being evaluated each
				# frame will be.
				#
				if (curFrame - self._startFrame) % self._frameStep != 0:
					continue
				
				nsm.Progress.setTitle("Frame %d" % curFrame)
				
				self._instancer.update()
				# Get the mapping of particle id to index in the per-particle
				# attribute arrays. This starts out 1-to-1 but changes as
				# particles die.
				#
				idMapper.fromParticle( self._dpParticle.node() )
				numParticles = fInstancer.particleCount()
	
				for particleIndex in range(0, numParticles):
					newTransformObj = MObject()
	
					particleId = idMapper.indexToId( particleIndex )
					if not self.isParticleSpecified( particleId ):
						continue
					
					objectIndex = self._instancer.getObjectIndex(particleIndex)
					if not self._instancer.getInstance( objectIndex ).root.isValid():
						# This shouldn't happen, but we should carry on
						# regardless.
						#
						assert 0
						continue
					
					uninstance = self._getUninstance( particleId )
					uninstance.bake( particleIndex )
	
				for uninstance in self._uninstances.values():
					uninstance.endFrame()
				nsm.Progress.advanceProgress( 1 )
					
			nsm.Progress.setTitle("Finalizing")
			result = []
			for uninstance in self._uninstances.values():
				uninstance.finalize()
				for path in uninstance.getPaths():
					result.append( path.partialPathName() )
			self.setResult( result )
			nsm.Progress.advanceProgress( 1 )
		finally:
			nsm.Progress.stop()
		
	def _getUninstance( self, particleId ):
		uninstance = None
		try:
			uninstance = self._uninstances[particleId]
		except KeyError, e:
			if eBake.geometry == self._bakeType:
				uninstance = StaticUninstance( self._instancer )
			elif eBake.animation == self._bakeType:
				uninstance = AnimatedUninstance( self._instancer )
			self._uninstances[particleId] = uninstance
		return uninstance
										
	def isParticleSpecified( self, particleId ):
		# TODO:
		# This may be able to be optimized since the MItInstancer
		# appears to iterate over the indices in ascending order.
		#
		# If no IDs were explicitly specified then we are acting
		# on the entire particle system. Otherwise an ID is only
		# specified it if can be found in the targetParticleIds
		# list
		return ( not self._targetParticleIds or
				 self._targetParticleIds.count( particleId ) )
			
	def undoIt( self ):
		if not self._hasBeenUndone:
			if self._copyAsInstance:
				# Remove all the children before deleting the parents.
				# Even though doIt() isn't called, MDGModifier still
				# does *something* when deleteNode(...) is first called
				#
				for uninstance in self._uninstances.values():
					for path in uninstance.getPaths():
						oDuplicate = path.transform()
						fDuplicate = MFnDagNode( oDuplicate )
						for j in range( fDuplicate.childCount(), 0, -1 ):
							self._mayaModifier.removeChildAt( oDuplicate, j-1 )
				self._mayaModifier.doIt()
		
			for uninstance in self._uninstances.values():
				for path in uninstance.getPaths():
					self._modifier.deleteNode( path.transform() )
				
			self._modifier.doIt()
			self._hasBeenUndone = True
	
		else:
			self._mayaModifier.doIt()
			self._modifier.doIt()

	def redoIt( self ):
		self._modifier.undoIt()
		self._mayaModifier.undoIt()
		
	def getCommandTarget( self, argData ):
		objects = MSelectionList()
		argData.getObjects(objects)
	
		# A plug is not a valid argument.
		#			
		try:
			plug = MPlug()
			# This will throw a RunTime error if there is no plug.
			# Which means:
			# if we catch a RunTime error -> success
			# if we *don't* catch a RunTime error -> failure, and throw
			# our BadArgumentError
			objects.getPlug( 0, plug )
			raise nspy.Errors.BadArgumentError("Please select a single particle instancer, single particle system, or some number of individual particles.")
		except RuntimeError, e:
			pass
	
		oTarget = MObject()
		objects.getDependNode( 0, oTarget )
		
		###########################################################################
		## An instancer was selected.
		##
		## 1. Get the instancer object
		## 2. Get the associated particle object
		###########################################################################
		if oTarget.hasFn( MFn.kInstancer ):
			# The instancer flag can not be used with an instancer target.
			#
			if argData.isFlagSet( kInstancerFlag ):
				raise nspy.Errors.BadArgumentError("The instancer flag can only be used with a particle system or particle command target.")
			if objects.length() > 1:
				raise nspy.Errors.BadArgumentError("Please select a single particle instancer, single particle system, or some number of individual particles.")

			objects.getDagPath( 0, self._dpInstancer )
			assert self._dpInstancer.hasFn( MFn.kInstancer )
	
			# Get the particle object and the instancer's index in its instanceData
			# array.
			#
			oParticle, instancerIndex = nsm.InstancerUtil.particle( self._dpInstancer )
			if not oParticle.hasFn( MFn.kParticle ):
				raise nspy.Errors.Error("No particle system associated with the instancer.")
			MDagPath.getAPathTo( oParticle, self._dpParticle )
			assert self._dpParticle.hasFn( MFn.kParticle )

		#####################################/
		# A particle system was selected.
		#
		# 1. Get the particle object
		# 2. Get the associated instancer, and throw an error if there isn't
		#	  exactly one.
		# 3. If individual particles were selected, get their component indices
		#	  and convert them to particle IDs.
		#####################################/
		elif oTarget.hasFn( MFn.kParticle ):
			MDagPath.getAPathTo( oTarget, self._dpParticle )
			assert self._dpParticle.hasFn( MFn.kParticle )
	
			if argData.isFlagSet( kInstancerFlag ):
				# The instancer flag was specified, this means that the user wants
				# to select which particle instancer associated with the give
				# particle object to uninstance.
				#
				instancerName = argData.flagArgumentString( kInstancerFlag, 0 )
	
				# Find the indicated instancer object.
				#
				list = MSelectionList()
				MGlobal.getSelectionListByName( instancerName, list )
				assert list.length() > 0
				
				oInstancer = MObject()
				list.getDependNode( 0, oInstancer )
				if not oInstancer.hasFn( MFn.kInstancer ):
					wrongNode = MFnDependencyNode( oInstancer )
					raise nspy.Errors.Error( wrongNode.name() +  " is not a particle instancer node." )
				list.getDagPath( 0, self._dpInstancer )
				assert self._dpInstancer.hasFn( MFn.kInstancer )
	
				# Verify that the indicated instancer object is associated
				# with the particle object specified as the command target.
				#
				oConnectedParticle, instancerIndex = nsm.InstancerUtil.particle( self._dpInstancer )
				if not oConnectedParticle == self._dpParticle.node():
					fInstancer = MFnInstancer( self._dpInstancer )
					fParticle = MFnParticleSystem( self._dpParticle )
					raise nspy.Errors.Error( fInstancer.name() +  " is not associated with " + fParticle.name() + "." )
			else:
				# No instancer flag is present - if the particle object only has
				# one associated instancer, use it, otherwise throw an error.
				#
				oInstancer = nsm.ParticleUtil.instancer(self._dpParticle)
				MDagPath.getAPathTo( oInstancer, self._dpInstancer )
				assert self._dpInstancer.hasFn( MFn.kInstancer )
	
			# Check to see if individual particles were specified. If so store
			# those particle IDs and only uninstance them.
			#
			dpParticle = MDagPath()
			oComponent = MObject()
			objects.getDagPath( 0, dpParticle, oComponent )
			if oComponent.isNull() and objects.length() > 1:
				# No components were found meaning that individual particles
				# were *not* specified - however the command has more than
				# one argument (which is invalid).
				#
				raise nspy.Errors.BadArgumentError("Please select a single particle instancer, single particle system, or some number of individual particles.")
			elif not oComponent.isNull():
				# Query the id mapping arrays so that we can convert the
				# selected components to particle ids.
				#
				idMapper = nsm.ParticleUtil.IdMapper()
				idMapper.fromParticle( self._dpParticle.node() )
	
				# Loop over all the specified components storing all their
				# indices.
				#
				argIndex = 0
				for argIndex in range(objects.length()):
					objects.getDagPath( argIndex, dpParticle, oComponent )
					if not dpParticle.hasFn( MFn.kParticle ):
						try:
							dpParticle.extendToShape()
						except:
							raise nspy.Errors.BadArgumentError("Please select a single particle instancer, single particle system, or some number of individual particles.")
						
					if oComponent.isNull() or not oComponent.hasFn( MFn.kSingleIndexedComponent ):
						# If one component is specified, all arguments must be
						# components.
						#
						raise nspy.Errors.BadArgumentError("Please select a single particle instancer, single particle system, or some number of individual particles.")
					if not dpParticle == self._dpParticle:
						raise nspy.Errors.BadArgumentError("All selected particles must be from the same particle system.")
					
					fComponent = MFnSingleIndexedComponent( oComponent )
					indices = MIntArray()
					fComponent.getElements( indices )
					i = 0
					for i in range( indices.length() ):
						self._targetParticleIds.append( idMapper.indexToId( indices[i] ) )
	
				# Sort the indices so we can use a binary search later.
				#
				self._targetParticleIds.sort()
		else:
			raise nspy.Errors.BadArgumentError("Please select a single particle instancer, single particle system, or some number of individual particles.")
	
		assert self._dpInstancer.isValid()
		assert self._dpParticle.isValid()
		
	def parseArg( self, argList ):
	#
	# Description:
	#		Initialize all data that won't change from frame to
	#		frame.
	#
	#		o command target (either instancer, particle system,
	#		  or individual particle ids)
	#		o number of instanced objects associated with the
	#		  instancer.
	#		o array of instanced objects.
	#		o start and end frames if specified.
	#
	#		NOTE: I believe it is technically possible for the
	#			  the number of instanced objects to change
	#			  during the simulation, but I think it's difficult
	#			  to do and I don't imagine very common.
	#
		try:
			argData = MArgDatabase( self.syntax(), argList )
		except:
			raise nspy.Errors.BadArgumentError("Please select a single particle instancer, single particle system, or some number of individual particles.")
		
		if argData.isFlagSet( kBakeTypeFlag ):
			bakeType = argData.flagArgumentString( kBakeTypeFlag, 0 )
			if bakeType == "geometry":
				self._bakeType = eBake.geometry
			elif bakeType == "animation":
				self._bakeType = eBake.animation
			else:
				raise  nspy.Errors.BadArgumentError( bakeType + " is not a valid bake type. Please use one of \"geometry\" or \"animation\"." )
		else:
			self._bakeType = eBake.geometry

		self._startFrame = int(MAnimControl.currentTime().value())
		self._endFrame = int(MAnimControl.currentTime().value())
		
		if argData.isFlagSet( kStartFrameFlag ):
			self._startFrame = argData.flagArgumentInt( kStartFrameFlag, 0 )
		if argData.isFlagSet( kEndFrameFlag ):
			self._endFrame = argData.flagArgumentInt( kEndFrameFlag, 0 )
		if argData.isFlagSet( kFrameStepFlag ):
			self._frameStep = argData.flagArgumentInt( kFrameStepFlag, 0 )
		if argData.isFlagSet( kCopyAsInstanceFlag ):
			self._copyAsInstance = argData.flagArgumentBool( kCopyAsInstanceFlag, 0 )

		maxRange = (self._endFrame - self._startFrame) + 4
		nsm.Progress.reset(maxRange)
		nsm.Progress.setTitle("Initializing")

		self.getCommandTarget( argData )
		
		self._instancer = Instancer( self._dpParticle, self._dpInstancer )
		self._instancer.reset( self._copyAsInstance, eBake.animation == self._bakeType )
		if self._instancer.numInstances() <= 0:
			raise nspy.Errors.Error("No shape associated with the instancer.")


		
		# When baking animation the instanced object itself
		# can't be animated - although its children can be so long
		# as we aren't baking to blendshapes (i.e. the objectIndex
		# associated with a given particleId never changes.
		#
		if eBake.animation == self._bakeType:
			for i in range( self._instancer.numInstances() ):
				if MAnimUtil.isAnimated( self._instancer.getInstance(i).root.transform() ):
					raise nspy.Errors.Error( "Instanced object " + self._instancer.getInstance(i).root.partialPathName() + " is animated. Bake type 'Animation' is unsupported." )

			
def cmdCreator():
	return OpenMayaMPx.asMPxPtr( UninstancerCmd() )

def syntaxCreator():
	syntax = MSyntax() 

	syntax.addFlag( kInstancerFlag, kInstancerFlagLong, MSyntax.kString )
	syntax.addFlag( kCopyAsInstanceFlag, kCopyAsInstanceFlagLong, MSyntax.kBoolean )
	syntax.addFlag( kStartFrameFlag, kStartFrameFlagLong, MSyntax.kLong )
	syntax.addFlag( kEndFrameFlag, kEndFrameFlagLong, MSyntax.kLong )
	syntax.addFlag( kFrameStepFlag, kFrameStepFlagLong, MSyntax.kLong )
	syntax.addFlag( kBakeTypeFlag, kBakeTypeFlagLong, MSyntax.kString )

	syntax.setObjectType( MSyntax.kSelectionList, 1 )
	syntax.useSelectionAsDefault( True )
	
	return syntax 
			
			