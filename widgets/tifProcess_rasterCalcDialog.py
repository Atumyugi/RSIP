import sys
import os
import os.path as osp

from appConfig import STRING_EXPRESSION_VALID,STRING_EXPRESSION_INVALID

from ui.tif_process_dialog.rasterCalcDialog import Ui_rasterCalcDialog

from PyQt5.QtCore import Qt, QPoint,QStringListModel
from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QVBoxLayout,QAbstractItemView,QFileDialog
from PyQt5.QtGui import QFont,QCursor

from qgis.core import QgsProject,QgsMapLayer,QgsMapLayerType,QgsLayerTreeGroup,QgsRasterLayer,QgsRectangle,QgsMapSettings,QgsCoordinateReferenceSystem
from qgis.gui import QgsMapCanvas,QgsProjectionSelectionDialog
from qgis.analysis import QgsRasterCalcNode,QgsRasterCalculatorEntry

from qfluentwidgets import (CardWidget, setTheme, Theme, IconWidget, BodyLabel,SubtitleLabel, CaptionLabel, PushButton,
                            TransparentToolButton, RoundMenu, Action,MessageBox)
from qfluentwidgets import FluentIcon as FIF

from widgets.tifProcess_child_selectCalcTemplateDialog import SelectCalcTemplateDialogClass

from yoyiUtils.qtTriggeredCommon import qtTriggeredCommonDialog
from yoyiUtils.yoyiFile import checkTifList
from yoyiUtils.yoyiTranslate import yoyiTrans

PROJECT = QgsProject.instance()

class RasterCalcDialogClass(Ui_rasterCalcDialog,QDialog):
    def __init__(self,yoyiTrs:yoyiTrans,rasterLayer,parent=None):
        super().__init__(parent)
        self.parentWindow = parent
        self.rasterLayer : QgsRasterLayer = rasterLayer
        self.yoyiTrs = yoyiTrs
        self.parentMapCanvas : QgsMapCanvas = self.parentWindow.mapCanvas
        self.setupUi(self)
        self.initMember()
        self.initUI()
        self.connectFunc()
    
    def initMember(self):
        self.rasterCalcNode = QgsRasterCalcNode()
        self.expression = None
        self.resPath = None
        self.format = None
        self.extent = None
        self.crs = None
        self.outWidth = None
        self.outHeight = None
    
    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        self.menu = RoundMenu(parent=self)
        self.crsDict = {}
        for layer in PROJECT.mapLayers().values():
            layer : QgsMapLayer
            self.crsDict[layer.name()] = f"{layer.crs().authid()}"
            action = Action(text=layer.name(),parent=self)
            action.setObjectName(f"action_{layer.name().split('.')[0]}")
            self.menu.addAction(action)
        
        self.bandStringList = []
        self.rasterCalcEntryList = []
        for i in range(self.rasterLayer.bandCount()):
            self.bandStringList.append(f"{self.rasterLayer.name()}@{i+1}")
            entry = QgsRasterCalculatorEntry()
            entry.bandNumber = i+1
            entry.raster = PROJECT.mapLayersByName(self.rasterLayer.name())[0]
            entry.ref = f"{self.rasterLayer.name()}@{i+1}"
            self.rasterCalcEntryList.append(entry)
        
        self.slm = QStringListModel()
        self.slm.setStringList(self.bandStringList)
        self.ListView.setModel(self.slm)
        self.ListView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        #self.ListView.clicked
        self.selectSaveFilePB.setIcon(FIF.MORE)
    
    def connectFunc(self):
        self.menu.triggered.connect(self.setLayerCrs)
        self.ListView.clicked.connect(self.ListViewClicked)
        self.TextEdit.textChanged.connect(self.checkExpressionValid)

        self.selectCalcTemplatePb.clicked.connect(self.selectCalcTemplatePbClicked)

        self.plusPb.clicked.connect(self.plusPbClicked)
        self.minusPb.clicked.connect(self.minusPbClicked)
        self.mulPb.clicked.connect(self.mulPbClicked)
        self.divPb.clicked.connect(self.divPbClicked)
        self.leftPb.clicked.connect(self.leftPbClicked)
        self.rightPb.clicked.connect(self.rightPbClicked)
        self.ifPb.clicked.connect(self.ifPbClicked)
        self.lessPb.clicked.connect(self.lessPbClicked)
        self.greaterPb.clicked.connect(self.greaterPbClicked)
        self.lessEqPb.clicked.connect(self.lessEqPbClicked)
        self.greaterEqPb.clicked.connect(self.greaterEqPbClicked)
        self.eqPb.clicked.connect(self.eqPbClicked)
        self.notEqPb.clicked.connect(self.notEqPbClicked)
        self.andPb.clicked.connect(self.andPbClicked)
        self.minPb.clicked.connect(self.minPbClicked)
        self.maxPb.clicked.connect(self.maxPbClicked)
        self.absPb.clicked.connect(self.absPbClicked)
        self.powPb.clicked.connect(self.powPbClicked)
        self.sqrtPb.clicked.connect(self.sqrtPbClicked)
        self.lnPb.clicked.connect(self.lnPbClicked)
        self.orPb.clicked.connect(self.orPbClicked)
        self.cosPb.clicked.connect(self.cosPbClicked)
        self.sinPb.clicked.connect(self.sinPbClicked)
        self.tanPb.clicked.connect(self.tanPbClicked)
        self.acosPb.clicked.connect(self.acosPbClicked)
        self.asinPb.clicked.connect(self.asinPbClicked)
        self.atanPb.clicked.connect(self.atanPbClicked)
        self.log10Pb.clicked.connect(self.log10PbClicked)
        self.ePb.clicked.connect(self.ePbClicked)
        self.paiPb.clicked.connect(self.paiPbClicked)

        self.selectMorePB.clicked.connect(self.selectMorePBClicked)
        self.selectMapcanvasCrsPB.clicked.connect(self.selectMapcanvasCrsPBClicked)
        self.selectSaveFilePB.clicked.connect(lambda: qtTriggeredCommonDialog().selectSaveFileTriggered(self.resLE,'tif',parent=self))
        self.runPB.clicked.connect(self.runPBClicked)
        self.cancelPB.clicked.connect(self.close)
        
    def checkExpressionValid(self):
        curStr = self.TextEdit.toPlainText()
        print(curStr)
        checkedStr = self.rasterCalcNode.parseRasterCalcString(curStr,"error")
        if checkedStr:
            self.expressionLabel.setText(STRING_EXPRESSION_VALID)
        else:
            self.expressionLabel.setText(STRING_EXPRESSION_INVALID)

    def selectCalcTemplatePbClicked(self):
        dialog = SelectCalcTemplateDialogClass(self.bandStringList,self)
        dialog.exec()
        if dialog.templateString:
            self.TextEdit.setText(dialog.templateString)
        dialog.deleteLater()

    def addString2TextEdit(self,strContent):
        self.TextEdit.setText( self.TextEdit.toPlainText() + strContent )

    def setLayerCrs(self,action):
        crs = self.crsDict[action.text()]
        self.targetCrsLE.setText(crs)
    
    def selectMorePBClicked(self):
        mapSetting : QgsMapSettings = self.parentMapCanvas.mapSettings()
        dialog = QgsProjectionSelectionDialog(self)
        dialog.setCrs(mapSetting.destinationCrs())
        dialog.exec()

        if dialog.hasValidSelection():
            self.targetCrsLE.setText(dialog.crs().authid())
        dialog.deleteLater()
    
    def selectMapcanvasCrsPBClicked(self):
        mapSetting : QgsMapSettings = self.parentMapCanvas.mapSettings()
        self.targetCrsLE.setText(mapSetting.destinationCrs().authid())

    
    def ListViewClicked(self):
        curIndex = self.ListView.currentIndex().row()
        if curIndex >=0:
            curStr = self.bandStringList[curIndex]
            self.addString2TextEdit(f" {curStr} ")

    def plusPbClicked(self):
        self.addString2TextEdit(" + ")
    
    def minusPbClicked(self):
        self.addString2TextEdit(" - ")
    
    def mulPbClicked(self):
        self.addString2TextEdit(" * ")
    
    def divPbClicked(self):
        self.addString2TextEdit(" / ")
    
    def leftPbClicked(self):
        self.addString2TextEdit(" ( ")
    
    def rightPbClicked(self):
        self.addString2TextEdit(" ) ")
    
    def ifPbClicked(self):
        self.addString2TextEdit(" if ( ")
    
    def lessPbClicked(self):
        self.addString2TextEdit(" < ")
    
    def greaterPbClicked(self):
        self.addString2TextEdit(" > ")

    def lessEqPbClicked(self):
        self.addString2TextEdit(" <= ")

    def greaterEqPbClicked(self):
        self.addString2TextEdit(" >= ")

    def eqPbClicked(self):
        self.addString2TextEdit(" = ")

    def notEqPbClicked(self):
        self.addString2TextEdit(" != ")

    def andPbClicked(self):
        self.addString2TextEdit(" AND ")

    def minPbClicked(self):
        self.addString2TextEdit(" MIN() ")

    def maxPbClicked(self):
        self.addString2TextEdit(" MAX() ")

    def absPbClicked(self):
        self.addString2TextEdit(" ABS() ")

    def powPbClicked(self):
        self.addString2TextEdit(" ^ ")

    def sqrtPbClicked(self):
        self.addString2TextEdit(" sqrt() ")

    def lnPbClicked(self):
        self.addString2TextEdit(" ln() ")

    def orPbClicked(self):
        self.addString2TextEdit(" OR ")

    def cosPbClicked(self):
        self.addString2TextEdit(" cos() ")

    def sinPbClicked(self):
        self.addString2TextEdit(" sin() ")

    def tanPbClicked(self):
        self.addString2TextEdit(" tan() ")

    def acosPbClicked(self):
        self.addString2TextEdit(" acos() ")

    def asinPbClicked(self):
        self.addString2TextEdit(" asin() ")

    def atanPbClicked(self):
        self.addString2TextEdit(" atan() ")

    def log10PbClicked(self):
        self.addString2TextEdit(" log10() ")

    def ePbClicked(self):
        self.addString2TextEdit(" 2.718281 ")

    def paiPbClicked(self):
        self.addString2TextEdit(" 3.141592 ")
    
    def runPBClicked(self):
        curStr = self.TextEdit.toPlainText()
        resString = self.rasterCalcNode.parseRasterCalcString(curStr,"error")
        if not resString:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('表达式无效!'), self).exec_()
            return
        if self.targetCrsLE.text() == "":
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('坐标系无效'), self).exec_()
            return
        if self.resLE.text() == "":
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('地址非法'), self).exec_()
            return
        

        self.expression = resString.toString()
        self.resPath = self.resLE.text()
        self.format = 'GTiff'
        self.extent = self.rasterLayer.extent()
        self.crs = QgsCoordinateReferenceSystem()
        self.crs.createFromString(self.targetCrsLE.text())
        self.outWidth = self.rasterLayer.width()
        self.outHeight = self.rasterLayer.height()

        self.close()

