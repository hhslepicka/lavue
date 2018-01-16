# Copyright (C) 2017  DESY, Christoph Rosemann, Notkestr. 85, D-22607 Hamburg
#
# lavue is an image viewing program for photon science imaging detectors.
# Its usual application is as a live viewer using hidra as data source.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation in  version 2
# of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor,
# Boston, MA  02110-1301, USA.
#
# Authors:
#     Christoph Rosemann <christoph.rosemann@desy.de>
#     Jan Kotanski <jan.kotanski@desy.de>
#

""" image widget """


import math

from PyQt4 import QtCore, QtGui

from . import imageDisplayWidget
import pyqtgraph as pg
import pyqtgraph.functions as fn



import pyqtgraph as pg
import numpy as np
import decimal, re
import ctypes
import sys, struct

try:
    import scipy.ndimage
    HAVE_SCIPY = True
    if pg.getConfigOption('useWeave'):
        try:
            import scipy.weave
        except ImportError:
            pg.setConfigOptions(useWeave=False)
except ImportError:
    HAVE_SCIPY = False
print("HAVE SP %s " %HAVE_SCIPY)



def affineSlice(data, shape, origin, vectors, axes, order=1, returnCoords=False, **kargs):
    """
    Take a slice of any orientation through an array. This is useful for extracting sections of multi-dimensional arrays such as MRI images for viewing as 1D or 2D data.
    
    The slicing axes are aribtrary; they do not need to be orthogonal to the original data or even to each other. It is possible to use this function to extract arbitrary linear, rectangular, or parallelepiped shapes from within larger datasets. The original data is interpolated onto a new array of coordinates using scipy.ndimage.map_coordinates (see the scipy documentation for more information about this).
    
    For a graphical interface to this function, see :func:`ROI.getArrayRegion <pyqtgraph.ROI.getArrayRegion>`
    
    ==============  ====================================================================================================
    Arguments:
    *data*          (ndarray) the original dataset
    *shape*         the shape of the slice to take (Note the return value may have more dimensions than len(shape))
    *origin*        the location in the original dataset that will become the origin of the sliced data.
    *vectors*       list of unit vectors which point in the direction of the slice axes. Each vector must have the same 
                    length as *axes*. If the vectors are not unit length, the result will be scaled relative to the 
                    original data. If the vectors are not orthogonal, the result will be sheared relative to the 
                    original data.
    *axes*          The axes in the original dataset which correspond to the slice *vectors*
    *order*         The order of spline interpolation. Default is 1 (linear). See scipy.ndimage.map_coordinates
                    for more information.
    *returnCoords*  If True, return a tuple (result, coords) where coords is the array of coordinates used to select
                    values from the original dataset.
    *All extra keyword arguments are passed to scipy.ndimage.map_coordinates.*
    --------------------------------------------------------------------------------------------------------------------
    ==============  ====================================================================================================
    
    Note the following must be true: 
        
        | len(shape) == len(vectors) 
        | len(origin) == len(axes) == len(vectors[i])
        
    Example: start with a 4D fMRI data set, take a diagonal-planar slice out of the last 3 axes
        
        * data = array with dims (time, x, y, z) = (100, 40, 40, 40)
        * The plane to pull out is perpendicular to the vector (x,y,z) = (1,1,1) 
        * The origin of the slice will be at (x,y,z) = (40, 0, 0)
        * We will slice a 20x20 plane from each timepoint, giving a final shape (100, 20, 20)
        
    The call for this example would look like::
        
        affineSlice(data, shape=(20,20), origin=(40,0,0), vectors=((-1, 1, 0), (-1, 0, 1)), axes=(1,2,3))
    
    """
    if not HAVE_SCIPY:
        raise Exception("This function requires the scipy library, but it does not appear to be importable.")

    # sanity check
    if len(shape) != len(vectors):
        raise Exception("shape and vectors must have same length.")
    if len(origin) != len(axes):
        raise Exception("origin and axes must have same length.")
    for v in vectors:
        if len(v) != len(axes):
            raise Exception("each vector must be same length as axes.")
        
    shape = list(map(np.ceil, shape))

    ## transpose data so slice axes come first
    trAx = list(range(data.ndim))
    for x in axes:
        trAx.remove(x)
    tr1 = tuple(axes) + tuple(trAx)
    data = data.transpose(tr1)
    #print "tr1:", tr1
    ## dims are now [(slice axes), (other axes)]
    

    ## make sure vectors are arrays
    if not isinstance(vectors, np.ndarray):
        vectors = np.array(vectors)
    if not isinstance(origin, np.ndarray):
        origin = np.array(origin)
    origin.shape = (len(axes),) + (1,)*len(shape)
    
    ## Build array of sample locations. 
    grid = np.mgrid[tuple([slice(0,x) for x in shape])]  ## mesh grid of indexes
    #print shape, grid.shape
    x = (grid[np.newaxis,...] * vectors.transpose()[(Ellipsis,) + (np.newaxis,)*len(shape)]).sum(axis=1)  ## magic
    x += origin
    #print "X values:"
    #print x
    ## iterate manually over unused axes since map_coordinates won't do it for us
    extraShape = data.shape[len(axes):]
    print(" empty %s %s %s" %(str(tuple(shape)), str(extraShape), data.dtype))
    output = np.empty(tuple(shape) + extraShape, dtype=data.dtype)
    for inds in np.ndindex(*extraShape):
        ind = (Ellipsis,) + inds
        #print data[ind].shape, x.shape, output[ind].shape, output.shape
        output[ind] = scipy.ndimage.map_coordinates(data[ind], x, order=order, **kargs)
    
    tr = list(range(output.ndim))
    trb = []
    for i in range(min(axes)):
        ind = tr1.index(i) + (len(shape)-len(axes))
        tr.remove(ind)
        trb.append(ind)
    tr2 = tuple(trb+tr)

    ## Untranspose array before returning
    output = output.transpose(tr2)
    if returnCoords:
        return (output, x)
    else:
        return output




def myget(self, data, img, axes=(0,1),
          returnMappedCoords=False, **kwds):

    shape, vectors, origin = self.getAffineSliceParams(data, img, axes)
    if not returnMappedCoords:
        print("D %s" % data)
        print("S %s" % shape)
        print("V %s" % str(vectors))
        print("OR %s" % str(origin))
        print("axes %s" % str(axes))
        print("ST %s" % str(self.state['size']))
        print("kwds %s" % str(kwds))
        return affineSlice(data, shape=shape, vectors=vectors, origin=origin, axes=axes, **kwds)
    else:
        kwds['returnCoords'] = True
        result, coords = fn.affineSlice(data, shape=shape, vectors=vectors, origin=origin, axes=axes, **kwds)



class ImageWidget(QtGui.QWidget):

    """
    The part of the GUI that incorporates the image view.
    """

    roiCoordsChanged = QtCore.pyqtSignal()
    cutCoordsChanged = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.nparray = None
        self.imageItem = None
        self.currentroimapper = QtCore.QSignalMapper(self)
        self.roiregionmapper = QtCore.QSignalMapper(self)
        self.currentcutmapper = QtCore.QSignalMapper(self)
        self.cutregionmapper = QtCore.QSignalMapper(self)

        verticallayout = QtGui.QVBoxLayout()
        filenamelayout = QtGui.QHBoxLayout()

        filelabel = QtGui.QLabel("Image/File name: ")
        filelabel.setToolTip("image or/and file name")

        filenamelayout.addWidget(filelabel)
        self.filenamedisplay = QtGui.QLineEdit()
        self.filenamedisplay.setReadOnly(True)
        self.filenamedisplay.setToolTip("image or/and file name")
        filenamelayout.addWidget(self.filenamedisplay)
        # self.buttonBox = QtGui.QDialogButtonBox()
        # self.quitButton  = self.buttonBox.addButton(
        #        QtGui.QDialogButtonBox.Close)
        # self.quitButton.setText("&Quit")
        self.quitButton = QtGui.QPushButton("&Quit")
        self.quitButton.setToolTip("quit the image viewer")
        self.cnfButton = QtGui.QPushButton("Configuration")
        self.cnfButton.setToolTip("image viewer configuration")
        self.loadButton = QtGui.QPushButton("Load")
        self.loadButton.setToolTip("load an image from a file")
        # self.buttonBox.addButton(self.cnfButton,
        #          QtGui.QDialogButtonBox.ActionRole)
        filenamelayout.addWidget(self.loadButton)
        filenamelayout.addWidget(self.cnfButton)
        filenamelayout.addWidget(self.quitButton)
        # filenamelayout.addWidget(self.buttonBox)
        verticallayout.addLayout(filenamelayout)

        self.splitter = QtGui.QSplitter(self)
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.img_widget = imageDisplayWidget.ImageDisplayWidget(
            parent=self.splitter)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred,
                                       QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(
            self.img_widget.sizePolicy().hasHeightForWidth())
        self.img_widget.setSizePolicy(sizePolicy)

        self.cutPlot = pg.PlotWidget(self.splitter)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred,
                                       QtGui.QSizePolicy.Preferred)
        self.cutCurve = self.cutPlot.plot()
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.cutPlot.sizePolicy().hasHeightForWidth())
        self.cutPlot.setSizePolicy(sizePolicy)
        self.cutPlot.setMinimumSize(QtCore.QSize(0, 120))

        verticallayout.addWidget(self.splitter)

        self.pixelComboBox = QtGui.QComboBox()
        self.pixelComboBox.addItem("Intensity")
        self.pixelComboBox.addItem("ROI")
        self.pixelComboBox.addItem("LineCut")
        self.pixelComboBox.setToolTip(
            "select the image tool for the mouse pointer,"
            " i.e. Intensity, ROI, LineCut")

        pixelvaluelayout = QtGui.QHBoxLayout()
        self.pixellabel = QtGui.QLabel("Pixel position and intensity: ")
        self.pixellabel.setToolTip(
            "coordinate info display for the mouse pointer")

        self.infodisplay = QtGui.QLineEdit()
        self.infodisplay.setReadOnly(True)
        self.infodisplay.setToolTip(
            "coordinate info display for the mouse pointer")

        self.roiLabel = QtGui.QLabel("ROI alias(es): ")
        self.roiLabel.setToolTip(
            "ROI alias or aliases related to sardana experimental channels")
        self.labelROILineEdit = QtGui.QLineEdit("")
        self.labelROILineEdit.setToolTip(
            "ROI alias or aliases related to Sardana Pool "
            "experimental channels")
        self.roiSpinBox = QtGui.QSpinBox()
        self.roiSpinBox.setMinimum(-1)
        self.roiSpinBox.setValue(1)
        self.roiSpinBox.setToolTip(
            "number of ROIs to add, -1 means remove ROI aliases from sardana")
        self.cutSpinBox = QtGui.QSpinBox()
        self.cutSpinBox.setMinimum(0)
        self.cutSpinBox.setValue(1)
        self.cutSpinBox.setToolTip(
            "number of Line Cuts")
        self.fetchROIButton = QtGui.QPushButton("Fetch")
        self.fetchROIButton.setToolTip(
            "fetch ROI aliases from the Door environment")
        self.applyROIButton = QtGui.QPushButton("Add")
        self.applyROIButton.setToolTip(
            "add ROI aliases to the Door environment "
            "as well as to Active MntGrp")

        pixelvaluelayout.addWidget(self.pixellabel)
        pixelvaluelayout.addWidget(self.infodisplay)
        pixelvaluelayout.addWidget(self.roiLabel)
        pixelvaluelayout.addWidget(self.labelROILineEdit)
        pixelvaluelayout.addWidget(self.roiSpinBox)
        pixelvaluelayout.addWidget(self.cutSpinBox)
        pixelvaluelayout.addWidget(self.applyROIButton)
        pixelvaluelayout.addWidget(self.fetchROIButton)
        pixelvaluelayout.addWidget(self.pixelComboBox)
        verticallayout.addLayout(pixelvaluelayout)

        self.setLayout(verticallayout)
        self.img_widget.currentMousePosition.connect(self.infodisplay.setText)

        self.roiregionmapper.mapped.connect(self.roiRegionChanged)
        self.currentroimapper.mapped.connect(self.currentROIChanged)
        self.img_widget.roi[0].sigHoverEvent.connect(self.currentroimapper.map)
        self.img_widget.roi[0].sigRegionChanged.connect(
            self.roiregionmapper.map)
        self.currentroimapper.setMapping(self.img_widget.roi[0], 0)
        self.roiregionmapper.setMapping(self.img_widget.roi[0], 0)

        self.cutCoordsChanged.connect(self.plotCut)
        self.roiSpinBox.valueChanged.connect(self.roiNrChanged)
        self.labelROILineEdit.textEdited.connect(self.updateROIButton)
        self.updateROIButton()

        self.cutregionmapper.mapped.connect(self.cutRegionChanged)
        self.currentcutmapper.mapped.connect(self.currentCutChanged)
        self.img_widget.cut[0].sigHoverEvent.connect(self.currentcutmapper.map)
        self.img_widget.cut[0].sigRegionChanged.connect(
            self.cutregionmapper.map)
        self.currentcutmapper.setMapping(self.img_widget.cut[0], 0)
        self.cutregionmapper.setMapping(self.img_widget.cut[0], 0)

        self.cutSpinBox.valueChanged.connect(self.cutNrChanged)

    @QtCore.pyqtSlot(int)
    def roiRegionChanged(self, _):
        self.roiChanged()

    @QtCore.pyqtSlot(int)
    def cutRegionChanged(self, cid):
        self.cutChanged()

    @QtCore.pyqtSlot(int)
    def currentROIChanged(self, rid):
        oldrid = self.img_widget.currentroi
        if rid != oldrid:
            self.img_widget.currentroi = rid
            self.roiCoordsChanged.emit()

    @QtCore.pyqtSlot(int)
    def currentCutChanged(self, cid):
        oldcid = self.img_widget.currentcut
        if cid != oldcid:
            self.img_widget.currentcut = cid
            self.cutCoordsChanged.emit()

    @QtCore.pyqtSlot()
    def updateROIButton(self):
        if not str(self.labelROILineEdit.text()).strip():
            self.applyROIButton.setEnabled(False)
        else:
            self.applyROIButton.setEnabled(True)

    @QtCore.pyqtSlot(int)
    def roiNrChanged(self, rid, coords=None):
        if rid < 0:
            self.applyROIButton.setText("Remove")
            self.applyROIButton.setToolTip(
                "remove ROI aliases from the Door environment"
                " as well as from Active MntGrp")
        else:
            self.applyROIButton.setText("Add")
            self.applyROIButton.setToolTip(
                "add ROI aliases to the Door environment "
                "as well as to Active MntGrp")
        if coords:
            for i, crd in enumerate(self.img_widget.roi):
                if i < len(coords):
                    self.img_widget.roicoords[i] = coords[i]
                    crd.setPos([coords[i][0], coords[i][1]])
                    crd.setSize(
                        [coords[i][2] - coords[i][0],
                         coords[i][3] - coords[i][1]])
        while rid > len(self.img_widget.roi):
            if coords and len(coords) >= len(self.img_widget.roi):
                self.img_widget.addROI(coords[len(self.img_widget.roi)])
            else:
                self.img_widget.addROI()
            self.img_widget.roi[-1].sigHoverEvent.connect(
                self.currentroimapper.map)
            self.img_widget.roi[-1].sigRegionChanged.connect(
                self.roiregionmapper.map)
            self.currentroimapper.setMapping(
                self.img_widget.roi[-1],
                len(self.img_widget.roi) - 1)
            self.roiregionmapper.setMapping(
                self.img_widget.roi[-1],
                len(self.img_widget.roi) - 1)
        if rid <= 0:
            self.img_widget.currentroi = -1
        elif self.img_widget.currentroi >= rid:
            self.img_widget.currentroi = 0
        while max(rid, 0) < len(self.img_widget.roi):
            self.currentroimapper.removeMappings(self.img_widget.roi[-1])
            self.roiregionmapper.removeMappings(self.img_widget.roi[-1])
            self.img_widget.removeROI()
        self.roiCoordsChanged.emit()
        self.roiSpinBox.setValue(rid)

    @QtCore.pyqtSlot(int)
    def cutNrChanged(self, cid, coords=None):
        if coords:
            for i, crd in enumerate(self.img_widget.cut):
                if i < len(coords):
                    self.img_widget.cutcoords[i] = coords[i]
                    crd.setPos([coords[i][0], coords[i][1]])
                    crd.setSize(
                        [coords[i][2] - coords[i][0],
                         coords[i][3] - coords[i][1]])
        while cid > len(self.img_widget.cut):
            if coords and len(coords) >= len(self.img_widget.cut):
                self.img_widget.addCut(coords[len(self.img_widget.cut)])
            else:
                self.img_widget.addCut()
            self.img_widget.cut[-1].sigHoverEvent.connect(
                self.currentcutmapper.map)
            self.img_widget.cut[-1].sigRegionChanged.connect(
                self.cutregionmapper.map)
            self.currentcutmapper.setMapping(
                self.img_widget.cut[-1],
                len(self.img_widget.cut) - 1)
            self.cutregionmapper.setMapping(
                self.img_widget.cut[-1],
                len(self.img_widget.cut) - 1)
        if cid <= 0:
            self.img_widget.currentcut = -1
        elif self.img_widget.currentcut >= cid:
            self.img_widget.currentcut = 0
        while max(cid, 0) < len(self.img_widget.cut):
            self.currentcutmapper.removeMappings(self.img_widget.cut[-1])
            self.cutregionmapper.removeMappings(self.img_widget.cut[-1])
            self.img_widget.removeCut()
        self.cutCoordsChanged.emit()
        self.cutSpinBox.setValue(cid)

    def roiChanged(self):
        try:
            rid = self.img_widget.currentroi
            state = self.img_widget.roi[rid].state
            ptx = int(math.floor(state['pos'].x()))
            pty = int(math.floor(state['pos'].y()))
            szx = int(math.floor(state['size'].x()))
            szy = int(math.floor(state['size'].y()))
            self.img_widget.roicoords[rid] = [ptx, pty, ptx + szx, pty + szy]
            self.roiCoordsChanged.emit()
        except Exception as e:
            print("Warning: %s" % str(e))

    def cutChanged(self):
        try:
            cid = self.img_widget.currentcut
            self.img_widget.cutcoords[cid] = \
                self.img_widget.cut[cid].getCoordinates()
            self.cutCoordsChanged.emit()
        except Exception as e:
            print("Warning: %s" % str(e))

    def showROIFrame(self):
        self.img_widget.vLine.hide()
        self.img_widget.hLine.hide()
        self.cutPlot.hide()
        self.fetchROIButton.show()
        self.applyROIButton.show()
        self.roiSpinBox.show()
        self.cutSpinBox.hide()
        self.labelROILineEdit.show()
        self.pixellabel.setText("[x1, y1, x2, y2]: ")
        self.roiLabel.show()
        for roi in self.img_widget.roi:
            roi.show()
        for cut in self.img_widget.cut:
            cut.hide()
        self.img_widget.cutenable = False
        self.img_widget.roienable = True
        self.img_widget.roi[0].show()
        self.infodisplay.setText("")

    def showIntensityFrame(self):
        self.pixellabel.setText("Pixel position and intensity: ")
        for roi in self.img_widget.roi:
            roi.hide()
        for cut in self.img_widget.cut:
            cut.hide()
        self.cutPlot.hide()
        self.fetchROIButton.hide()
        self.labelROILineEdit.hide()
        self.applyROIButton.hide()
        self.roiSpinBox.hide()
        self.cutSpinBox.hide()
        self.roiLabel.hide()
        self.img_widget.roienable = False
        self.img_widget.cutenable = False
        self.img_widget.vLine.show()
        self.img_widget.hLine.show()
        self.infodisplay.setText("")

    def showLineCutFrame(self):
        self.pixellabel.setText("Cut, pixel position and intensity: ")
        for roi in self.img_widget.roi:
            roi.hide()
        for cut in self.img_widget.cut:
            cut.show()
        self.cutPlot.show()
        self.fetchROIButton.hide()
        self.labelROILineEdit.hide()
        self.applyROIButton.hide()
        self.cutSpinBox.show()
        self.roiSpinBox.hide()
        self.roiLabel.hide()
        self.img_widget.roienable = False
        self.img_widget.cutenable = True
        self.img_widget.vLine.show()
        self.img_widget.hLine.show()
        self.infodisplay.setText("")

    def plot(self, array, name=None, rawarray=None):
        if array is None:
            return
        if rawarray is None:
            rawarray = array
        if name is not None:
            self.filenamedisplay.setText(name)

        self.img_widget.updateImage(array, rawarray)
        if self.img_widget.cutenable:
            self.plotCut()
            
    @QtCore.pyqtSlot()
    def plotCut(self):
        cid = self.img_widget.currentcut
        if cid > -1 and len(self.img_widget.cut) > cid:
            cut = self.img_widget.cut[cid]
            print("C %s" % cut)
            print("R %s" % self.img_widget.rawdata)
            print("I %s" % self.img_widget.image)
            if self.img_widget.rawdata is not None:
                dt = myget(cut,
                           self.img_widget.rawdata,
                           self.img_widget.image, axes=(0, 1))
                dt = cut.getArrayRegion(
                    self.img_widget.rawdata,
                    self.img_widget.image, axes=(0, 1))
                while dt.ndim > 1:
                    dt = dt.mean(axis=1)
                self.cutCurve.setData(y=dt)
                self.cutPlot.setVisible(True)
                self.cutCurve.setVisible(True)
                return
        self.cutCurve.setVisible(False)

    @QtCore.pyqtSlot(int)
    def setAutoLevels(self, autoLvls):
        self.img_widget.setAutoLevels(autoLvls)

    @QtCore.pyqtSlot(float)
    def setMinLevel(self, level=None):
        self.img_widget.setDisplayMinLevel(level)

    @QtCore.pyqtSlot(float)
    def setMaxLevel(self, level=None):
        self.img_widget.setDisplayMaxLevel(level)

    @QtCore.pyqtSlot(str)
    def changeGradient(self, name):
        self.img_widget.updateGradient(name)
