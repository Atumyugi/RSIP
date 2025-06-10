import sys
import os
import os.path as osp

from ui.shp_process_dialog.shpBufferDialog import Ui_shpBufferDialog

from PyQt5.QtCore import Qt, QPoint,QVariant
from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QVBoxLayout
from PyQt5.QtGui import QFont

from qgis.core import QgsProject,QgsMapLayer,QgsMapLayerType,QgsWkbTypes,QgsRasterLayer,QgsVectorLayer,QgsField,QgsRectangle,QgsMapSettings
from qgis.gui import QgsMapCanvas

from qfluentwidgets import (CardWidget, setTheme, Theme, IconWidget, BodyLabel,SubtitleLabel, CaptionLabel, PushButton,
                            TransparentToolButton, RoundMenu, Action,MessageBox)
from qfluentwidgets import FluentIcon as FIF

from yoyiUtils.qtTriggeredCommon import qtTriggeredCommonDialog
from yoyiUtils.yoyiFile import checkTifList
from yoyiUtils.yoyiTranslate import yoyiTrans
import yoyirs_rc

PROJECT = QgsProject.instance()

class ShpBufferDialogClass(Ui_shpBufferDialog,QDialog):
    def __init__(self,yoyiTrs:yoyiTrans,parent=None):
        super().__init__(parent)
        self.parentWindow = parent
        self.yoyiTrs = yoyiTrs
        self.setupUi(self)
        self.initMember()
        self.initUI()
        self.connectFunc()
    
    def initMember(self):
        self.shpPath = None
        self.resPath = None
        self.distance = None
        self.segments = None
        self.endStyle = None
        self.joinStyle = None
        self.miterLimit = None
        self.dissolve = None
    
    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        for layer in PROJECT.mapLayers().values():
            layer : QgsMapLayer
            if layer.type() == QgsMapLayerType.VectorLayer and layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                self.selectShpCb.addItem(layer.name())
        self.selectSaveFilePB.setIcon(FIF.MORE)

        self.endStyleCb.addItems(["圆角(Rounded)","扁平(Flat)","方角(Sharp)"])
        self.endStyleCb.setCurrentIndex(0)

        self.joinStyleCb.addItems(["圆角(Rounded)","尖角(Acute)","斜角(Beveled)"])
        self.joinStyleCb.setCurrentIndex(0)

    def connectFunc(self):
        self.selectSaveFilePB.clicked.connect(lambda: qtTriggeredCommonDialog().selectSaveFileTriggered(self.resLE,'shp',parent=self))
        self.runPB.clicked.connect(self.runPBClicked)
        self.cancelPB.clicked.connect(self.close)
    
    def runPBClicked(self):
        if self.resLE.text() == "":
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('地址非法'), self).exec_()
            return
        if self.selectShpCb.count() == 0:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('没有有效矢量'), self).exec_()
            return
        currentLayerName = self.selectShpCb.currentText()
        currentLayer : QgsVectorLayer = PROJECT.mapLayersByName(currentLayerName)[0]

        self.shpPath = currentLayer.source()
        self.resPath = self.resLE.text()
        self.distance = self.distanceSpinBox.value()
        self.segments = self.segmentsSpinBox.value()
        self.endStyle = self.endStyleCb.currentIndex()
        self.joinStyle = self.joinStyleCb.currentIndex()
        self.miterLimit = self.miterLimitSpinBox.value()
        self.dissolve = self.dissolveCheckBox.isChecked()

        self.close()