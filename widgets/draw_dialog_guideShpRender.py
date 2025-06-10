import datetime
import os
import os.path as osp
import re
import traceback

from ui.draw_dialog.guideShpRenderDialog import Ui_guidShpRenderDialog

from PyQt5.QtCore import QVariant,QStringListModel,pyqtSignal,Qt
from PyQt5 import QtCore
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QVBoxLayout,QWidget,QAbstractItemView,QMenu, QAction,QUndoStack,QMainWindow,QDesktopWidget,QDialog,QColorDialog,QMessageBox,QSizePolicy,QProgressBar,QDockWidget,QFileDialog,QHBoxLayout,QApplication
from qgis.core import QgsCategorizedSymbolRenderer,QgsLayerTreeModel,QgsRectangle,QgsFeature,QgsFillSymbol,QgsRasterLayer,QgsProject,Qgis,QgsColorRampShader\
    ,QgsPalettedRasterRenderer,QgsVectorLayer,QgsField,QgsVectorFileWriter,QgsTextFormat,\
    QgsPalLayerSettings,QgsVectorLayerSimpleLabeling,QgsSimpleLineSymbolLayer,QgsSingleSymbolRenderer,QgsGeometry
from qgis.gui import QgsLayerTreeMapCanvasBridge,QgsLayerTreeView,QgsMessageBar,QgsMapToolIdentifyFeature,QgsMapCanvas,QgsMapToolPan
import traceback
from qfluentwidgets import MessageBox,ColorPickerButton,SubtitleLabel,setFont

from widgets.projectListDialog import LocalProjectListDialogClass
from widgets.draw_dialog_createSegProject  import SegDrawCreateProjectDialogClass

from yoyiUtils.custom_maptool import *
from yoyiUtils.yoyiRenderProp import yoyiShpPropClass,createShpLabel
from yoyiUtils.yoyiFile import readYamlToDict,checkTifList,saveSampleWorkYaml
from yoyiUtils.qgisLayerUtils import getFIDlist
from yoyiUtils.qgisFunction import saveShpFunc

from appConfig import *


PROJECT = QgsProject.instance()

class GuideShpRenderDialogClass(Ui_guidShpRenderDialog,QDialog):
    shpRenderChanged = pyqtSignal(list)
    def __init__(self,layer,parent=None):
        super().__init__(parent)
        self.parentWindow = parent
        self.setupUi(self)

        self.yspc = yoyiShpPropClass()
        self.layer: QgsVectorLayer = layer
        self.initMember()
        self.initUI()
        self.connectFunc()

    def initMember(self):
        self.defaultRenderType = 0
        self.defaultColorR = 255
        self.defaultColorG = 0
        self.defaultColorB = 0
        self.defaultOutLine = 0.7
        self.defaultDistanceSpinBox = 10

    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        self.setObjectName("shpRender" + self.layer.id())

        if (type(self.layer.renderer()) != QgsCategorizedSymbolRenderer) and self.layer.renderer() != None:
            renderType, colorR, colorG, colorB, renderOutline = self.yspc.getDialogProp(self.layer)
            #  0 空心 1 实心 2 空心线条填充
            self.btnColor = QColor(colorR, colorG, colorB)
            self.colorBtn = ColorPickerButton(self.btnColor, '渲染颜色选择', parent=self.parent(), enableAlpha=True)
            self.horizontalLayout_Color.addWidget(self.colorBtn)
            if renderType == 0:
                self.lineRender.setChecked(True)
                self.distanceSpinBox.setEnabled(False)
            elif renderType == 1:
                self.fillRender.setChecked(True)
                self.distanceSpinBox.setEnabled(False)
            else:
                self.fillLineRender.setChecked(True)
                self.distanceSpinBox.setEnabled(False)
            self.alphaSlider.setValue(int(float(self.layer.renderer().symbol().opacity()) * 100))
            self.outlineSpinBox.setValue(renderOutline)

    def connectFunc(self):
        self.renderButtonGroup.buttonClicked.connect(self.renderButtonGroupButtonClicked)
        self.savePb.clicked.connect(self.savePbClicked)

    def renderButtonGroupButtonClicked(self):
        if self.lineRender.isChecked():
            self.distanceSpinBox.setEnabled(False)
        elif self.fillRender.isChecked():
            self.distanceSpinBox.setEnabled(False)
        else:
            self.distanceSpinBox.setEnabled(True)


    def savePbClicked(self):
        color = self.colorBtn.color.name()
        print(color)
        lineWidth = str(self.outlineSpinBox.value())
        opacity = self.alphaSlider.value() / 100
        distance = self.distanceSpinBox.value()
        if self.lineRender.isChecked():
            self.layer.setRenderer(self.yspc.createDiySymbol(color,lineWidth,isFull=False))
        elif self.fillRender.isChecked():
            self.layer.setRenderer(self.yspc.createDiySymbol(color,isFull=True))
        else:
            self.layer.setRenderer(self.yspc.createDiySymbol(color,isFull=True,fullPattern="line",distance=distance))
        self.layer.setOpacity(opacity)
        self.layer.triggerRepaint()

        self.shpRenderChanged.emit([self.layer.name(),self.fillRender.isChecked(),self.colorBtn.color])
