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

""" gradient choice widget """

from PyQt4 import QtCore, QtGui


class GradientChoiceWidget(QtGui.QGroupBox):

    """
    Select how an image should be transformed.
    """

    chosenGradient = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        QtGui.QGroupBox.__init__(self, parent)

        self.setTitle("Gradient choice")

        layout = QtGui.QHBoxLayout()
        self.cb = QtGui.QComboBox()
        self.cb.addItem("reversegrey")
        self.cb.addItem("highcontrast")
        self.cb.addItem("thermal")
        self.cb.addItem("flame")
        self.cb.addItem("bipolar")
        self.cb.addItem("spectrum")
        self.cb.addItem("spectrumclip")
        self.cb.addItem("greyclip")
        self.cb.addItem("grey")
        self.cb.addItem("cyclic")
        self.cb.addItem("yellowy")
        self.cb.addItem("inverted")
        layout.addWidget(self.cb)
        self.setLayout(layout)
        self.cb.activated.connect(self.emitText)

    @QtCore.pyqtSlot(int)
    def emitText(self, index):
        self.chosenGradient.emit(self.cb.itemText(index))

    @QtCore.pyqtSlot(str)
    def changeGradient(self, name):
        text = self.cb.currentText()
        if text != name:
            cid = self.cb.findText(name)
            if cid > -1:
                self.cb.setCurrentIndex(cid)
            else:
                print("Error %s" % name)