
import datetime
import os
import os.path as osp
import re
import traceback

from ui.measureDistanceDialog import Ui_measureDistanceDialog

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

DistanceUnitList = ["米(Meters)","千米(Kilometers)","英尺(Feet)","海里(NauticalMiles)",
                    "码(Yards)","英里(Miles)","度(Degrees)","厘米(Centimeters)","毫米(Millimeters)"]

class MeasureDistanceMapToolDialogClass(Ui_measureDistanceDialog,QDialog):
    listCleared = pyqtSignal(int)
    ellipsoidChanged = pyqtSignal(int)
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
        self.tempItems : list[QListWidgetItem] = []
        self.tempValues = []
        self.saveTotalValue = 0.0
        self.lastTempValue = 0.0

    def initUI(self):
        self.unitCb.addItems(DistanceUnitList)
        self.unitCb.setCurrentIndex(0)
        
    def connectFunc(self):
        self.unitCb.currentIndexChanged.connect(self.itemsUpdate)
        self.decimalPrecisionSpinBox.valueChanged.connect(self.itemsUpdate)
        self.autoTransUnitCheckBox.stateChanged.connect(self.itemsUpdate)

        self.clearPb.clicked.connect(self.itemsClear)
        self.baseModeButtonGroup.buttonToggled.connect(self.baseModeButtonGroupToggled)
    
    def itemsUpdate(self):
        for index,tempValue in enumerate(self.tempValues):
            tempItem = self.tempItems[index]
            tempValueTransUnit = self.distanceArea.formatDistance(tempValue,
                                                              self.decimalPrecisionSpinBox.value(),
                                                              self.unitCb.currentIndex(),
                                                              not self.autoTransUnitCheckBox.isChecked())
            tempItem.setText(tempValueTransUnit)
        
        self.changeLastItem(self.lastTempValue)
    
    def itemsClear(self):
        self.ListWidget.clear()
        self.tempItems = []
        self.tempValues = []
        self.listCleared.emit(0)

    def baseModeButtonGroupToggled(self):
        if self.baseInCartesianCb.isChecked():
            self.ellipsoidChanged.emit(0)
        else:
            self.ellipsoidChanged.emit(1)
    
    def addTempListWidget(self):
        
        if len(self.tempItems) == 0:
            pass
        else:
            self.tempValues.append(self.lastTempValue)
        
        self.saveTotalValue = 0.0
        for tempValue in self.tempValues:
            self.saveTotalValue += tempValue

        tempItem = QListWidgetItem("0.0",self.ListWidget)
        self.tempItems.append(tempItem)
        self.ListWidget.addItem(tempItem)

        self.ListWidget.setCurrentRow(self.ListWidget.count()-1)
        self.ListWidget.scrollToBottom()

    def changeLastItem(self,value):
        tempItem = self.tempItems[-1]
        tempValueTransUnit = self.distanceArea.formatDistance(value,
                                                              self.decimalPrecisionSpinBox.value(),
                                                              self.unitCb.currentIndex(),
                                                              not self.autoTransUnitCheckBox.isChecked())
        tempItem.setText(tempValueTransUnit)

        tempTotalValue = value + self.saveTotalValue
        tempTotalValueTransUnit = self.distanceArea.formatDistance(tempTotalValue,
                                                              self.decimalPrecisionSpinBox.value(),
                                                              self.unitCb.currentIndex(),
                                                              not self.autoTransUnitCheckBox.isChecked())
        self.totalLE.setText(tempTotalValueTransUnit)

        self.lastTempValue = value
    
