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

""" preparationbox widget """

from PyQt4 import QtGui

from . import transformationsWidget
from . import maskWidget
from . import bkgSubtractionWidget


class QHLine(QtGui.QFrame):
    """ horizontal line
    """

    def __init__(self):
        """ constructor
        """
        QtGui.QFrame.__init__(self)

        self.setFrameShape(QtGui.QFrame.HLine)
        self.setFrameShadow(QtGui.QFrame.Sunken)


class PreparationGroupBox(QtGui.QGroupBox):
    """ colection of image preperation widgets
    """

    def __init__(self, parent=None):
        """ constructor

        :param parent: parent object
        :type parent: :class:`PyQt4.QtCore.QObject`
        """
        QtGui.QGroupBox.__init__(self, parent)
        self.setTitle("Image preparation")

        #: (:obj:`bool`) show mask
        self.__mask = True

        #: (:class:`lavuelib.maskWidget.Maskwidget`) mask widget
        self.maskWg = maskWidget.MaskWidget(parent=self)
        #: (:class:`lavuelib.bkgSubtractionWidget.BkgSubtractionWidget`)
        #  background subtrantion widget
        self.bkgSubWg = bkgSubtractionWidget.BkgSubtractionWidget(parent=self)
        self.__hline = QHLine()
        #: (:class:`lavuelib.transformationsWidget.TransformationsWidget`)
        #  transformations widget
        self.trafoWg = transformationsWidget.TransformationsWidget(parent=self)

        vlayout = QtGui.QVBoxLayout()
        vlayout.addWidget(self.bkgSubWg)
        vlayout.addWidget(self.maskWg)
        vlayout.addWidget(self.__hline)
        vlayout.addWidget(self.trafoWg)

        self.setLayout(vlayout)

    def changeView(self, showmask=False):
        """ show or hide widgets in the preparation colection

        :param showmask: is mask shown
        :type showmask: :obj:`bool`
        """

        if showmask:
            self.__mask = True
            self.maskWg.show()
        else:
            self.__mask = False
            self.maskWg.hide()
