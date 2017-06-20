"""
Extension to GraphicsWidget displaying a gradient editor, afaiu
"""


import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph.functions as fn
from pyqtgraph import GraphicsWidget
from pyqtgraph.graphicsItems.ViewBox import *
from pyqtgraph.graphicsItems.GradientEditorItem import *
from pyqtgraph.graphicsItems.AxisItem import *
from pyqtgraph.graphicsItems.GridItem import *


import pyqtgraph.functions as fn

import numpy as np


pg.graphicsItems.GradientEditorItem.Gradients['inverted'] = {'ticks': [(0.0, (255, 255, 255, 255)), (1.0, (0, 0, 0, 255)),], 'mode': 'rgb'}
pg.graphicsItems.GradientEditorItem.Gradients['highContrast'] = {'ticks': [(0.0, (0, 0, 0, 255)), (1.0, (255, 255, 0, 255)),], 'mode': 'rgb'}

class GradientItem(GraphicsWidget):
    """
    This is a blatant copy/rewrite of the HistogramLUTItem.
    Instead of a histogram and stuff it only provides a
    Gradient editor to define color lookup table for single-channel images.
    In addition, it can set different predefined gradients by function.
    """
    
    sigLookupTableChanged = QtCore.Signal(object)
    sigLevelsChanged = QtCore.Signal(object)
    sigLevelChangeFinished = QtCore.Signal(object)
    
    def __init__(self, image=None, fillHistogram=True):
        """
        If *image* (ImageItem) is provided, then the control will be automatically linked to the image and changes to the control will be immediately reflected in the image's appearance.
        """
        GraphicsWidget.__init__(self)
        self.lut = None
        self.imageItem = None
        
        self.layout = QtGui.QGraphicsGridLayout()
        self.setLayout(self.layout)
        self.layout.setContentsMargins(1,1,1,1)
        self.layout.setSpacing(0)
        
        self.vb = ViewBox()
        self.vb.setMaximumWidth(152)
        self.vb.setMinimumWidth(45)
        self.vb.setMouseEnabled(x=False, y=False)
        
        self.gradient = GradientEditorItem()
        self.gradient.tickSize = 0 # CR: this is  sooooo bad, but there is no function !?
        self.gradient.setOrientation('right')
        self.gradient.loadPreset('inverted')
        
        self.layout.addItem(self.gradient, 0, 0)
        
        self.range = None
        self.gradient.setFlag(self.gradient.ItemStacksBehindParent)
        
        self.vb.setFlag(self.gradient.ItemStacksBehindParent)
        
        self.gradient.sigGradientChanged.connect(self.gradientChanged)
        
        if image is not None:
            self.setImageItem(image)
        
    def paint(self, p, *args):
        pass

    def setImageItem(self, img):
        self.imageItem = img
        img.setLookupTable(self.getLookupTable)  ## send function pointer, not the result
   
    def gradientChanged(self):
        if self.imageItem is not None:
            if self.gradient.isLookupTrivial():
                self.imageItem.setLookupTable(None)
            else:
                self.imageItem.setLookupTable(self.getLookupTable)  ## send function pointer, not the result
            
        self.lut = None

    def getLookupTable(self, img=None, n=None, alpha=None):
        if n is None:
            if img.dtype == np.uint8:
                n = 256
            else:
                n = 512
        if self.lut is None:
            self.lut = self.gradient.getLookupTable(n, alpha=alpha)
        return self.lut

    def setGradientByName(self, name):
        try:
            self.gradient.loadPreset(str(name))
        except:
            self.gradient.loadPreset("highContrast")
