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
from maya.OpenMayaFX import *


import ns.py as nspy
import ns.py.Const

import ns
import ns.maya as nsm
import ns.maya.uninstancer
import ns.maya.ParticleUtil
from ns.maya.uninstancer.Geometry import *

				
	
class eInstancerCycle:
	noCycle, sequential, numValues = range(3)
	
class eInstancerCycleUnit:
	frames, seconds, numValues = range(3)
					
class Instancer:
	
	def __init__(self, dpParticle, dpInstancer):
		self._cycleType = eInstancerCycle.noCycle
		self._numInstances = 0
		self._instances = []
		self._matrices = []
		self._objectIndices = MIntArray()
		self._blendShapes = []
		self._copyAsInstance = False
		
		self._fParticle = MFnParticleSystem( dpParticle )
		self.fInstancer = MFnInstancer( dpInstancer )
		(oParticle, self._instancerIndex) = nsm.InstancerUtil.particle( dpInstancer )

	def numInstances(self):
		return self._numInstances
	
	def hasBlendShapes(self):
		return bool(self._blendShapes)
	
	def copyAsInstance(self):
		return self._copyAsInstance

	def getInstance(self, index):
		return self._instances[index]
	
	def getMatrix(self, index):
		return self._matrices[index]
	
	def startFrame(self):
		aStartFrame = self._fParticle.attribute( "startFrame" )
		return MPlug( self._fParticle.object(), aStartFrame ).asInt()
	
	def duplicateInstance(self, index):
		if self._blendShapes:
			if self._blendShapes[index]:
				return self._blendShapes[index].duplicate( self._copyAsInstance, "" )
			else:
				blendShape = BlendShape( self._numInstances )
				blendShape.setBaseShape( self._instances[index].duplicate( False, "_#" ) )
				for i in range( self._numInstances ):
					blendShape.addBlendShapeTarget( self._instances[i], i )
				blendShape.keyWeight( MAnimControl.currentTime(), -1 )
				self._blendShapes[index] = blendShape
				return blendShape
		else:
			return self._instances[index].duplicate( self._copyAsInstance, "_#" )
	
	def getObjectIndex(self, particleIndex):
		objectIndex = 0
		if self._objectIndices:
			assert particleIndex < len( self._objectIndices )
			objectIndex = self._objectIndices[ particleIndex ]
			
			if objectIndex >= self._numInstances:
				# It seems that when an index is used that is greater
				# than the total number of instanced shapes, Maya uses
				# the last instanced shape instead.
				#
				objectIndex = self._numInstances - 1
			
		assert self._instances[ objectIndex ].root.isValid()
		return objectIndex
	
	def reset(self, copyAsInstance, bakeAnimation):
		self._copyAsInstance = copyAsInstance
		aCycle = self.fInstancer.attribute( "cycle" )
		self._cycleType = MPlug( self.fInstancer.object(), aCycle ).asInt()
	
		aHierarchyCount = self.fInstancer.attribute("hierarchyCount")
		self._numInstances = MPlug( self.fInstancer.object(), aHierarchyCount ).asInt()

		if (copyAsInstance and
		    bakeAnimation and
		    eInstancerCycle.sequential == self._cycleType and
		    self._numInstances > 1):
			self._blendShapes =  [ None for i in range(self._numInstances) ]

		self._instances = [ Geometry() for i in range(self._numInstances) ]
		for i in range( self._numInstances ):
			self._instances[i].fromInstancer( self.fInstancer.dagPath(), i )
	
	def update(self):	
		# Per-particle indices to consider. Find all of the instanced
		# objects' base matrices and determine the per-particle index
		# values.
		#
		self._fillMatrices()
		self._fillObjectIndices()
		
		if self._blendShapes and self._numInstances:
			time = MAnimControl.currentTime()
			for i in range( self._numInstances ):
				if self._blendShapes[i]:
					self._blendShapes[i].keyWeight( time, (i+1) % self._numInstances )
			prev = self._blendShapes[self._numInstances-1]
			for i in range( self._numInstances ):
				temp = self._blendShapes[i]
				self._blendShapes[i] = prev
				prev = temp
		
	def _fillMatrices( self ):
		'''Store the appropriate base transforms of the instanced
		   objects (their base transform post-multiplied by any
		   transforms from the DAG paths above them).'''
		  		
		self._matrices = []
		for i in range(self._numInstances):
			oInstance = self._instances[i].root.transform()
			fInstance = MFnTransform( oInstance )
			matrix = MMatrix( fInstance.transformation().asMatrix() )
			# The particle instancer uses the first path
			# to the object if it has DAG instances.
			#
			if not fInstance.parent(0).hasFn( MFn.kWorld ):
				path = MDagPath()
				MDagPath.getAPathTo( oInstance, path )
				matrix *= path.exclusiveMatrix()
			
			self._matrices.append( matrix )
			
	def _fillObjectIndices( self ):
		self._objectIndices.clear()
		
		if ( self._numInstances > 1 ):
			# If there are more than one instanced object then we have
			# to check for per-particle object indices. There are
			# two ways to specify this:
			# 1. By mapping a per-particle attribute to the objectIndex
			#    option.
			# 2. By enabling automatice object cycling.
			#
			aIndex = nsm.ParticleUtil.mappedAttribute( self._fParticle.dagPath(),
													   "objectIndex",
													   self._instancerIndex )
			if aIndex:
				nsm.ParticleUtil.getPerParticleIntData( self._fParticle.dagPath(),
														aIndex,
														self._objectIndices )
			elif eInstancerCycle.sequential == self._cycleType:
				self._sequentialObjectIndices()
					
	def _sequentialObjectIndices( self ):
		# Get per-particle age
		#
		aAge = nsm.ParticleUtil.mappedAttribute( self._fParticle.dagPath(),
												 "age",
												 self._instancerIndex ) or "age"
		ageData = MDoubleArray()
		nsm.ParticleUtil.getPerParticleDoubleData( self._fParticle.dagPath(),
												   aAge,
												   ageData )
		
		# What object index does a given particle start on?
		#
		aCycleStart = nsm.ParticleUtil.mappedAttribute( self._fParticle.dagPath(),
														"cycleStartObject",
														self._instancerIndex )
		cycleStartData = MIntArray()
		if aCycleStart:
			nsm.ParticleUtil.getPerParticleIntData( self._fParticle.dagPath(),
													aCycleStart,
													cycleStartData )
		else:
			cycleStartData = MIntArray( ageData.length(), 0 )
		
		# The number of steps to take (in either frames or seconds)
		#
		step = nsm.DG.getPlug( node=self.fInstancer.object(), attrName="cycleStep" ).asDouble()
		
		# Whether to count steps in seconds or frames
		#
		unit = nsm.DG.getPlug( node=self.fInstancer.object(), attrName="cycleStepUnit" ).asInt()
		
		if eInstancerCycleUnit.frames == unit:
			# If the instancer is counting in frames, convert to seconds
			# for simplicity.
			#
			step *= nsm.Utils.secondsPerFrame()
		
		numParticles = self.fInstancer.particleCount()
		self._objectIndices.setLength( numParticles )
		
		for i in range( numParticles ):
			# Calculate the current instanced object index by dividing the
			# particle's age (in seconds) by the step size (in seconds).
			# The cycle start object defines which index we should start
			# counting from.
			#
			# It looks like Maya rounds the index result to 3 decimal places
			# before truncating it to an int.
			#
			index = int( round( ageData[i] / step, 3 ) )
			index = (cycleStartData[i] + index) % self._numInstances
			self._objectIndices[i] = index
