# author: Ch. Rosemann, DESY
# email: christoph.rosemann@desy.de


# first try for a live viewer image display
# base it on a qt dialog
# this is just the formal definition of the graphical elements !

import pyqtgraph as pg
import math
import numpy as np

from PyQt4 import QtCore, QtGui
import sys


class gui_definition(QtGui.QDialog):

    def __init__(self, parent=None, signal_host=None, target=None):
        super(gui_definition, self).__init__(parent)

        vlayout = QtGui.QVBoxLayout()
        self.hw = hidra_widget(parent = self)
        self.isw = intensityscaling_widget(parent = self)
        self.lsw = limits_widget(parent = self)
        self.stats = statistics_widget(parent = self)
        self.img_w = image_widget(parent = self)

        globallayout = QtGui.QHBoxLayout()
        
        self.raw_image = None
        self.image_name = None

        # define grid elements
        vlayout.addWidget(self.hw)
        vlayout.addWidget(self.isw)
        vlayout.addWidget(self.stats)
        vlayout.addWidget(self.lsw)

        globallayout.addLayout(vlayout)
        globallayout.addWidget(self.img_w)

        self.setLayout(globallayout)

        self.setWindowTitle("Live Image Viewer")

        self.isw.changeScaling.connect(self.replot)
        self.lsw.limitsChanged.connect(self.img_w.setLimits)
        self.img_w.limitsHaveChanged.connect(self.replot)

    def plot(self, nparr, name):
        self.image_name = name
        self.raw_image = nparr
        self.img_w.plot(nparr, self.isw.getCurrentScaling(), name)
        self.stats.setMaxMeanVar(np.amax(nparr), np.mean(nparr), np.var(nparr))

    def replot(self, style=None):
        if style is None:
            self.img_w.plot(self.raw_image, self.isw.getCurrentScaling())
        else:
            self.stats.setMaxMeanVar(np.amax(self.raw_image), np.mean(self.raw_image), np.var(self.raw_image))
            self.stats.changeScaling(style)
            self.img_w.plot(self.raw_image, style)



class hidra_widget(QtGui.QGroupBox):

    """
    Connect and disconnect hidra service.
    """

    def __init__(self, parent=None, signal_host=None, target=None):
        super(hidra_widget, self).__init__(parent)
        self.setTitle("HiDRA connection")
        
        self.signal_host = signal_host
        self.target = target
        self.connected = False
        # grid/table layout:
        # | label:         | server name/details |
        # | connect button |  status display     |
        gridlayout = QtGui.QGridLayout()

        self.widget00 = QtGui.QLabel(u"HiDRA server")
        self.serverName = QtGui.QLabel(u"SomeName")
        self.widget10 = QtGui.QLabel("Status")
        self.widget11 = QtGui.QLineEdit("Not connected")
        #~ self.widget20 = QtGui.QLineEdit("Not connected")
        self.widget21 = QtGui.QPushButton("Connect")

        self.widget21.clicked.connect(self.toggleServerConnection)

        gridlayout.addWidget(self.widget00, 0, 0)
        gridlayout.addWidget(self.serverName, 0, 1)
        gridlayout.addWidget(self.widget10, 1, 0)
        gridlayout.addWidget(self.widget11, 1, 1)
        gridlayout.addWidget(self.widget21, 2, 1)

        self.setLayout(gridlayout)
    
    def setServerName(self, name):
        self.serverName.setText(name)

    def toggleServerConnection(self):
        if(not self.connected):
            try:
                establish_hidra_connection(self.signal_host, self.target)
            except:
                print("Big big connect error")
                return

        self.connected = not self.connected

        if(self.connected):
            self.widget11.setText("Connected")
        else:
            self.widget11.setText("Not connected")


class imagesettings_widget(QtGui.QWidget):

    """
    Control the image settings.
    """

    def __init__(self, parent=None):
        super(imagesettings_widget, self).__init__(parent)

        # two columns layout:
        # | radiobuttons       | checkboxes |
        columnlayout = QtGui.QHBoxLayout()

        leftw = intensityscaling_widget()
        rightw = limitsetting_widget()

        columnlayout.addWidget(leftw)
        columnlayout.addWidget(rightw)

        self.setLayout(columnlayout)


class intensityscaling_widget(QtGui.QGroupBox):

    """
    Select how the image intensity is supposed to be scaled.
    """
    changeScaling = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super(intensityscaling_widget, self).__init__(parent)
        
        self.setTitle("Intensity display")
        self.current = "sqrt"
        verticallayout = QtGui.QVBoxLayout()

        self.linbutton = QtGui.QRadioButton(u"linear")
        self.logbutton = QtGui.QRadioButton(u"log")
        self.sqrtbutton = QtGui.QRadioButton(u"sqrt")

        self.linbutton.toggled.connect(self.setCurrentScaling)
        self.logbutton.toggled.connect(self.setCurrentScaling)
        self.sqrtbutton.toggled.connect(self.setCurrentScaling)
        self.sqrtbutton.setChecked(True)

        verticallayout.addWidget(self.linbutton)
        verticallayout.addWidget(self.logbutton)
        verticallayout.addWidget(self.sqrtbutton)

        self.setLayout(verticallayout)

    def getCurrentScaling(self):
        return self.current

    def setCurrentScaling(self, scaling):
        if self.linbutton.isChecked():
            self.changeScaling.emit("lin")
        elif self.logbutton.isChecked():
            self.changeScaling.emit("log")
        else:
            self.changeScaling.emit("sqrt")


class limits_widget(QtGui.QGroupBox):

    """
    Set minimum and maximum displayed values.
    """
    
    limitsChanged = QtCore.pyqtSignal(float, float)

    def __init__(self, parent=None):
        super(limits_widget, self).__init__(parent)
        
        self.setTitle("Set display limits")
        layout = QtGui.QGridLayout()
        
        minLabel = QtGui.QLabel("minimum value: ")
        maxLabel = QtGui.QLabel("maximum value: ")
        
        self.minVal = QtGui.QDoubleSpinBox()
        self.maxVal = QtGui.QDoubleSpinBox()

        self.applyButton = QtGui.QPushButton("Apply limits")

        layout.addWidget(minLabel,0,0  )
        layout.addWidget(self.minVal,0,1 )
        layout.addWidget(maxLabel,1,0  )
        layout.addWidget(self.maxVal,1,1 )
        layout.addWidget(self.applyButton,2,1 )
        
        self.setLayout(layout)
        self.applyButton.clicked.connect(self.broadcast_limits)

    def broadcast_limits(self):
        self.limitsChanged.emit(self.minVal.value(), self.maxVal.value())

class statistics_widget(QtGui.QGroupBox):

    """
    Display some general image statistics.
    """

    def __init__(self, parent=None):
        super(statistics_widget, self).__init__(parent)
        
        self.setTitle("Image statistics")
        layout = QtGui.QGridLayout()
        
        self.scaling = "sqrt"
        
        scalingLabel = QtGui.QLabel("Scaling:")
        self.scaleLabel = QtGui.QLabel(self.scaling)
        
        maxlabel = QtGui.QLabel("maximum: ")
        meanlabel = QtGui.QLabel("mean: ")
        variancelabel = QtGui.QLabel("variance: ")
        
        self.maxVal = QtGui.QLineEdit("Not set")
        self.meanVal = QtGui.QLineEdit("Not set")
        self.varVal = QtGui.QLineEdit("Not set")
        layout.addWidget(scalingLabel, 0, 0)
        layout.addWidget(self.scaleLabel, 0,1)
        
        layout.addWidget(maxlabel,1,0  )
        layout.addWidget(self.maxVal,1,1 )
        layout.addWidget(meanlabel,2,0  )
        layout.addWidget(self.meanVal,2,1  )
        layout.addWidget(variancelabel,3,0  )
        layout.addWidget( self.varVal,3,1 )
        
        self.setLayout(layout)

    def setMaxMeanVar(self, mx, mean, var):
        if self.scaling == "lin":
            self.maxVal.setText(str("%.4f" % mx))
            self.meanVal.setText(str("%.4f" % mean))
            self.varVal.setText(str("%.4f" % var))
        elif self.scaling == "sqrt":
            self.maxVal.setText(str("%.4f" % math.sqrt(mx)))
            self.meanVal.setText(str("%.4f" % math.sqrt(mean)))
            self.varVal.setText(str("%.4f" % math.sqrt(var)))
        elif self.scaling == "log":
            self.maxVal.setText(str("%.4f" % math.log(mx)))
            self.meanVal.setText(str("%.4f" % math.log(mean)))
            self.varVal.setText(str("%.4f" % math.log(var)))
        self.show()

    def changeScaling(self, scaling):
        if self.scaling != scaling:
            self.scaling = scaling
            self.scaleLabel.setText(self.scaling)


class imagetransformations_widget(QtGui.QWidget):

    """
    Select how an image should be transformed.
    """

    def __init__(self, parent=None):
        super(imagetransformations_widget, self).__init__(parent)

        verticallayout = QtGui.QVBoxLayout()

        flip = QtGui.QCheckBox(u"flip")
        mirror = QtGui.QCheckBox(u"mirror")
        rotate90 = QtGui.QCheckBox(u"rotate90")

        verticallayout.addWidget(flip)
        verticallayout.addWidget(mirror)
        verticallayout.addWidget(rotate90)

        self.setLayout(verticallayout)


class image_widget(QtGui.QWidget):

    """
    The part of the GUI that incorporates the image view.
    """
    
    limitsHaveChanged = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(image_widget, self).__init__(parent)

        self.nparray = None
        self.crosshair_locked = False
        self.imageItem = None
        self.levels = [None, None] # the limits of drawing
        self.levelsSet = False

        # the actual image is an item of the PlotWidget
        self.img_widget = pg.PlotWidget()
        self.img_widget.scene().sigMouseMoved.connect(self.mouse_position)
        self.img_widget.scene().sigMouseClicked.connect(self.mouse_click)

        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen=(255, 0, 0))
        self.hLine = pg.InfiniteLine(angle=0, movable=False, pen=(255, 0, 0))

        verticallayout = QtGui.QVBoxLayout()

        self.filenamedisplay = QtGui.QLineEdit()
        verticallayout.addWidget(self.filenamedisplay)

        verticallayout.addWidget(self.img_widget)

        self.infodisplay = QtGui.QLineEdit()
        verticallayout.addWidget(self.infodisplay)

        self.setLayout(verticallayout)

    def mouse_position(self, event):

        try:
            mousePoint = self.imageItem.mapFromScene(event)
            xdata = math.floor(mousePoint.x())
            ydata = math.floor(mousePoint.y())

            if not self.crosshair_locked:
                self.vLine.setPos(xdata)
                self.hLine.setPos(ydata)

            intensity = self.nparray[math.floor(xdata), math.floor(ydata)]
            self.infodisplay.setText("x=%.2f, y=%.2f, intensity=%.4f"
                                     % (xdata, ydata, intensity))
        except:
            self.infodisplay.setText("error")

    def mouse_click(self, event):

        mousePoint = self.imageItem.mapFromScene(event.scenePos())

        xdata = mousePoint.x()
        ydata = mousePoint.y()

        # if double click: fix mouse crosshair
        # another double click releases the crosshair again
        #~ if event.double():
            #~ self.crosshair_locked = not self.crosshair_locked
            #~ 
            #~ if not self.crosshair_locked:
                #~ self.vLine.setPos(xdata)
                #~ self.hLine.setPos(ydata)

    def plot(self, nparr, style, name=None):
        if name is not None:
            self.filenamedisplay.setText(name)
        self.nparray = nparr
        if not self.levelsSet:
            self.levels[0] = np.amin(nparr)
            self.levels[1] = np.amax(nparr)
        if style == "lin":
            drawarray = nparr
            self.levels = [ math.floor(self.levels[0]), math.ceil(self.levels[1])]
        elif style == "log":
            drawarray = np.log10(nparr)
            if self.levels[0] <= 0:
                self.levels[0] = 10e-6
            self.levels = [ math.log10(self.levels[0]), math.log10(self.levels[1])]
        elif style == "sqrt":
            drawarray = np.sqrt(nparr)
            self.levels = [ math.sqrt(self.levels[0]), math.sqrt(self.levels[1])]
        else:
            print("Chosen display style '" + style + "' is not valid.")
            return

        if self.imageItem is None:
            self.imageItem = pg.ImageItem(drawarray, levels=self.levels)
            self.img_widget.addItem(self.imageItem)
            self.img_widget.addItem(self.vLine, ignoreBounds=True)
            self.img_widget.addItem(self.hLine, ignoreBounds=True)
        else:
            self.imageItem.setImage(drawarray, levels=self.levels)

    def setLimits(self,lowlim, uplim):
        if self.levels[0] != lowlim or self.levels[1] != uplim:
            self.levelsSet = True
            self.levels = [lowlim, uplim]
            self.limitsHaveChanged.emit()
            

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    dialog = gui_definition(signal_host="haspp03pilatus.desy.de",
                            target=[["haspp03.desy.de", "50111", 0, [".cbf"]]])
    from PyQt4 import QtTest

    i=1
    dialog.show()
    while True:
        rand_arr = 10*np.random.rand(100, 100)
        dialog.plot(rand_arr,"random number test nr. " + str(i))
        i += 1
        QtTest.QTest.qWait(2000)
