import datetime
import os
import os.path as osp
import re
import traceback

from ui.measureAreaDialog import Ui_measureAreaDialog

from PyQt5.QtCore import QVariant,QStringListModel,pyqtSignal,Qt
from PyQt5 import QtCore
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QListWidgetItem,QWidget,QAbstractItemView,QMenu, QAction,QUndoStack,QMainWindow,QDesktopWidget,QDialog,QColorDialog,QMessageBox,QSizePolicy,QProgressBar,QDockWidget,QFileDialog,QHBoxLayout,QApplication
from qgis.core import QgsDistanceArea,QgsLayerTreeModel,QgsRectangle,QgsFeature,QgsFillSymbol,QgsRasterLayer,QgsProject,Qgis,QgsColorRampShader\
    ,QgsPalettedRasterRenderer,QgsVectorLayer,QgsField,QgsVectorFileWriter,QgsTextFormat,\
    QgsPalLayerSettings,QgsVectorLayerSimpleLabeling,QgsSimpleLineSymbolLayer,QgsSingleSymbolRenderer,QgsGeometry
from qgis.gui import QgsLayerTreeMapCanvasBridge,QgsLayerTreeView,QgsMessageBar,QgsMapToolIdentifyFeature,QgsMapCanvas,QgsMapToolPan
import traceback
from qfluentwidgets import MessageBox,ColorPickerButton,SubtitleLabel,setFont

from yoyiUtils.yoyiRenderProp import yoyiShpPropClass,createShpLabel
from yoyiUtils.yoyiFile import readYamlToDict,checkTifList,saveSampleWorkYaml
from yoyiUtils.qgisLayerUtils import getFIDlist
from yoyiUtils.qgisFunction import saveShpFunc

from appConfig import *

PROJECT = QgsProject.instance()

AreaUnitList = ["平方米(SquareMeters)","平方千米(SquareKilometers)","平方英尺(SquareFeet)",
                "平方码(SquareYards)","平方英里(SquareMiles)","公顷(Hectares)","英亩(Acres)"]

class MeasureAreaMapToolDialogClass(Ui_measureAreaDialog,QDialog):
    ellipsoidChanged = pyqtSignal(int)
    cleared = pyqtSignal(int)

    def __init__(self,distanceArea:QgsDistanceArea, parent=None) -> None:
        super().__init__(parent)

        self.distanceArea = distanceArea

        self.setupUi(self)

        self.initPosition()
        self.initMember()
        self.initUI()
        self.connectFunc()
    
    def initPosition(self):
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move(int((screen.width() - size.width()) / 1.03), int((screen.height() - size.height()) / 10))
    
    def initMember(self):
        self.tempValue = 0.0
    
    def initUI(self):
        self.unitCb.addItems(AreaUnitList)
        self.unitCb.setCurrentIndex(0)
    
    def connectFunc(self):
        self.unitCb.currentIndexChanged.connect(lambda : self.changeItem(self.tempValue))
        self.decimalPrecisionSpinBox.valueChanged.connect(lambda : self.changeItem(self.tempValue))
        self.autoTransUnitCheckBox.stateChanged.connect(lambda : self.changeItem(self.tempValue))

        self.clearPb.clicked.connect(self.itemClear)
        self.baseModeButtonGroup.buttonToggled.connect(self.baseModeButtonGroupToggled)

    def itemClear(self):
        self.changeItem(0)
        self.cleared.emit(0)

    def baseModeButtonGroupToggled(self):
        if self.baseInCartesianCb.isChecked():
            self.ellipsoidChanged.emit(0)
        else:
            self.ellipsoidChanged.emit(1)
    
    def changeItem(self,value):

        tempValueTransUnit = self.distanceArea.formatArea(value,
                                                          self.decimalPrecisionSpinBox.value(),
                                                          self.unitCb.currentIndex(),
                                                          not self.autoTransUnitCheckBox.isChecked())
        
        self.totalLE.setText(tempValueTransUnit)

        self.tempValue = value
