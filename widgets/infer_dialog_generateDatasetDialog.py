import sys
import os
import os.path as osp

from ui.infer_dialog.generateDatasetDialog import Ui_generateDatasetDialog

from PyQt5.QtCore import Qt, QPoint,QVariant,QDate
from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QVBoxLayout
from PyQt5.QtGui import QFont

from qgis.core import QgsProject,QgsMapLayer,QgsMapLayerType,QgsWkbTypes,QgsVectorLayer,QgsRasterLayer,QgsRectangle,QgsMapSettings,QgsField
from qgis.gui import QgsMapCanvas

from qfluentwidgets import (CardWidget, setTheme, Theme, IconWidget, BodyLabel,SubtitleLabel, CaptionLabel, PushButton,
                            TransparentToolButton, RoundMenu, Action,MessageBox)
from qfluentwidgets import FluentIcon as FIF

from widgets.draw_dialog_pixelClassifyMapWindow import PixelClassifyMapWindowClass

from yoyiUtils.qtTriggeredCommon import qtTriggeredCommonDialog
from yoyiUtils.yoyiFile import checkTifList,checkShpList,filterMultiBandTif,checkFileListByList
from yoyiUtils.yoyiTranslate import yoyiTrans
from yoyiUtils.yoyiDialogThread import calFieldUniqueValuesRunClass

PROJECT = QgsProject.instance()

class GenerateDatasetDialogClass(Ui_generateDatasetDialog,QDialog):
    def __init__(self,yoyiTrs:yoyiTrans,parent=None):
        super().__init__(parent)
        self.parentWindow = parent
        self.yoyiTrs = yoyiTrs
        self.parentMapCanvas : QgsMapCanvas = self.parentWindow.mapCanvas
        self.setupUi(self)
        self.initMember()
        self.initUI()
        self.connectFunc()

    def initMember(self):
        self.mode = None
        self.tifPathList = None
        self.tifPathListII = None
        self.resDir = None
        self.shpPathList = None
        self.needTransRgb = None
        self.overlap = None
        self.imgSize = None
        self.dropZero = None
        self.generatePost = None
        self.shpField = None
        self.shpFieldII = None
        self.shpPixelMapping = None
        self.diyPixelValue = None
        self.classDict = None
        self.mosaicShp = None
        self.mosaicShpII = None
        self.mosaicShpImgidField = None
        self.mosaicShpImgidFieldII = None
        self.imgIdTime = None
        self.imgIdTimeII = None
        self.initIndex = None
        self.sampleName = None
        self.sampleDescription = None
        self.sampleBuilder = None
        self.imageAreaId = None
        self.isObb = None
        self.clipMinAreaPer = None
        self.filePre = None

    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        
        # icon
        self.selectExTifPb.setIcon(FIF.MORE)
        self.selectExTifIIPb.setIcon(FIF.MORE)
        self.selectExShpPb.setIcon(FIF.MORE)
        self.selectSaveFilePB.setIcon(FIF.MORE)

        # visible
        self.sampleModePbGroupClicked()

        self.IndeterminateProgressBar.hide()

        # time
        self.ZhDatePicker.setDate(QDate(2014,12,1))
        self.ZhDatePickerII.setDate(QDate(2014,12,1))
        

        # layer
        for layer in PROJECT.mapLayers().values():
            layer : QgsMapLayer
            layerSourcePath: str = layer.source()
            if layerSourcePath.split(".")[-1] in ["tif", "TIF", "TIFF", "GTIFF"]:
                self.selectTifCb.addItem(layer.name())
                self.selectTifIICb.addItem(layer.name())
            elif layer.type() == QgsMapLayerType.VectorLayer and layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                self.selectShpCb.addItem(layer.name())
                self.selectMosaicCb.addItem(layer.name())
                self.selectMosaicCbII.addItem(layer.name())
        
        self.refreshShpField()
        self.refreshMosaicField()
        self.refreshMosaicFieldII()

        # default Name
        self.sampleNameLE.setText("XXX")
        self.sampleDescriptionLE.setText("XXX")
        self.sampleBuilderLE.setText("XXX")

        # default Index
        self.initIndexSpinBox.setValue(1)
        
    
    def connectFunc(self):
        self.sampleModePbGroup.buttonClicked.connect(self.sampleModePbGroupClicked)
        self.selectShpCb.currentIndexChanged.connect(self.refreshShpField)
        self.selectMosaicCb.currentIndexChanged.connect(self.refreshMosaicField)
        self.selectMosaicCbII.currentIndexChanged.connect(self.refreshMosaicFieldII)
        # 双checkbox 同步
        self.selectShpFieldCheckBox.clicked.connect(self.selectShpFieldCheckBoxClicked)
        self.selectShpIIFieldCheckBox.clicked.connect(self.selectShpIIFieldCheckBoxClicked)

        self.selectExTifPb.clicked.connect(lambda: qtTriggeredCommonDialog().addFileDirTriggered(self.selectTifCb,
                                                                                                       parent=self,
                                                                                                       lineEditType="ComboBox"))
        
        self.selectExShpPb.clicked.connect(lambda: qtTriggeredCommonDialog().addFileDirTriggered(self.selectShpCb,
                                                                                                       parent=self,
                                                                                                       lineEditType="ComboBox"))

        self.selectExTifIIPb.clicked.connect(lambda: qtTriggeredCommonDialog().addFileDirTriggered(self.selectTifIICb,
                                                                                                   parent=self,
                                                                                                   lineEditType="ComboBox"))
        self.selectSaveFilePB.clicked.connect(lambda: qtTriggeredCommonDialog().addFileDirTriggered(self.resLE,parent=self))
        
        self.runPB.clicked.connect(self.runPBClicked)

    def sampleModePbGroupClicked(self):
        status = self.CDRb.isChecked()
        self.selectTifIILabel.setEnabled(status)
        self.selectTifIICb.setEnabled(status)
        self.selectExTifIIPb.setEnabled(status)
        self.selectShpIIFieldCheckBox.setEnabled(status)
        self.selectShpIIFieldCb.setEnabled(status)
        self.mosaicModeRbII.setEnabled(status)
        self.selectMosaicCbII.setEnabled(status)
        self.selectMosaicFieldCbII.setEnabled(status)
        self.diyTimeModeRbII.setEnabled(status)
        self.ZhDatePickerII.setEnabled(status)
    
    def refreshShpField(self):
        currentLayerName = self.selectShpCb.text()
        if currentLayerName != "":
            if osp.isdir(currentLayerName):
                if len(checkShpList(currentLayerName)) >0:
                    layerSource = checkShpList(currentLayerName)[0]
                else:
                    MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('没有有效图层'), self).exec_()
                    self.selectShpCb.removeItem(0)
                    return
            else:
                layerSource = PROJECT.mapLayersByName(self.selectShpCb.currentText())[0].source()
            currentLayer : QgsVectorLayer = QgsVectorLayer(layerSource)
            self.selectShpFieldCb.clear()
            self.selectShpIIFieldCb.clear()
            for field in currentLayer.fields():
                field : QgsField
                print(field.type())
                if field.type() in [QVariant.Type.Int,QVariant.Type.UInt,QVariant.Type.LongLong,QVariant.Type.ULongLong]:
                    self.selectShpFieldCb.addItem(text=field.name(),icon=":/img/resources/int.png")
                    self.selectShpIIFieldCb.addItem(text=field.name(),icon=":/img/resources/int.png")
                elif field.type() in [QVariant.Type.Double]:
                    self.selectShpFieldCb.addItem(text=field.name(),icon=":/img/resources/float.png")
                    self.selectShpIIFieldCb.addItem(text=field.name(),icon=":/img/resources/float.png")
                elif field.type() in [QVariant.Type.String]:
                    self.selectShpFieldCb.addItem(text=field.name(),icon=":/img/resources/str.png")
                    self.selectShpIIFieldCb.addItem(text=field.name(),icon=":/img/resources/str.png")
            del currentLayer
    
    def refreshMosaicField(self):
        currentLayerName = self.selectMosaicCb.text()
        if currentLayerName != "":
            currentLayer : QgsVectorLayer = PROJECT.mapLayersByName(currentLayerName)[0]
            self.selectMosaicFieldCb.clear()
            diyIndex = 0
            for index,field in enumerate(currentLayer.fields()):
                field : QgsField
                if field.type() in [QVariant.Type.Int,QVariant.Type.UInt,QVariant.Type.LongLong,QVariant.Type.ULongLong]:
                    self.selectMosaicFieldCb.addItem(text=field.name(),icon=":/img/resources/int.png")
                elif field.type() in [QVariant.Type.Double]:
                    self.selectMosaicFieldCb.addItem(text=field.name(),icon=":/img/resources/float.png")
                elif field.type() in [QVariant.Type.String]:
                    self.selectMosaicFieldCb.addItem(text=field.name(),icon=":/img/resources/str.png")
                if field.name() == "ImageSourc":
                    diyIndex = index
            self.selectMosaicFieldCb.setCurrentIndex(diyIndex)
    
    def refreshMosaicFieldII(self):
        currentLayerName = self.selectMosaicCbII.text()
        if currentLayerName != "":
            currentLayer : QgsVectorLayer = PROJECT.mapLayersByName(currentLayerName)[0]
            self.selectMosaicFieldCbII.clear()
            diyIndex = 0
            for index,field in enumerate(currentLayer.fields()):
                field : QgsField
                if field.type() in [QVariant.Type.Int,QVariant.Type.UInt,QVariant.Type.LongLong,QVariant.Type.ULongLong]:
                    self.selectMosaicFieldCbII.addItem(text=field.name(),icon=":/img/resources/int.png")
                elif field.type() in [QVariant.Type.Double]:
                    self.selectMosaicFieldCbII.addItem(text=field.name(),icon=":/img/resources/float.png")
                elif field.type() in [QVariant.Type.String]:
                    self.selectMosaicFieldCbII.addItem(text=field.name(),icon=":/img/resources/str.png")
                if field.name() == "ImageSourc":
                    diyIndex = index
            self.selectMosaicFieldCbII.setCurrentIndex(diyIndex)
    
    def selectShpFieldCheckBoxClicked(self):
        self.selectShpIIFieldCheckBox.setChecked(self.selectShpFieldCheckBox.isChecked())

    def selectShpIIFieldCheckBoxClicked(self):
        self.selectShpFieldCheckBox.setChecked(self.selectShpIIFieldCheckBox.isChecked())
        
    def runPBClicked(self):
        if self.selectTifCb.count() == 0:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('没有有效图层'), self).exec_()
            return
        
        if self.CDRb.isChecked():
            if self.selectTifCb.currentText() == self.selectTifIICb.currentText():
                MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('前后期影像一致'), self).exec_()
                return

        selectTifCbText = self.selectTifCb.currentText()
        if osp.isdir(selectTifCbText):
            tifIsDir = True
            tifPathList = checkTifList(selectTifCbText)
        else:
            tifIsDir = False
            tifPathList = [PROJECT.mapLayersByName(selectTifCbText)[0].source()]
        tifPathList = filterMultiBandTif(tifPathList)

        if tifPathList == []:
            MessageBox(self.yoyiTrs._translate('警告'), f"{self.yoyiTrs._translate('没有有效影像')} {self.yoyiTrs._translate('请检查波段数量大于3,数据类型为Uint8')}", self).exec_()
            return

        if self.CDRb.isChecked():
            selectTifIICbText = self.selectTifIICb.currentText()
            if osp.isdir(selectTifIICbText):
                tifIsDirII = True
                tifPathListII = checkTifList(selectTifIICbText)
            else:
                tifIsDirII = False
                tifPathListII = [PROJECT.mapLayersByName(selectTifIICbText)[0].source()]
            
            if tifIsDir != tifIsDirII:
                MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('不能前后期影像一个是文件一个是文件夹'), self).exec_()
                return
            
            if tifPathListII == []:
                MessageBox(self.yoyiTrs._translate('警告'), f"{self.yoyiTrs._translate('没有有效影像')} {self.yoyiTrs._translate('请检查波段数量大于3,数据类型为Uint8')}", self).exec_()
                return
        else:
            selectTifIICbText = None
            tifPathListII = []
        
        selectShpCbText = self.selectShpCb.currentText()
        if osp.isdir(selectShpCbText):  
            if tifIsDir: 
                # 情况1 都是文件夹 
                tifPathList,shpPathList,tifPathListII = checkFileListByList(tifPathList,selectShpCbText,extraFolder=selectTifIICbText)
            else:
                # 情况2 矢量是文件夹   影像是文件
                MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('影像和矢量一个是文件一个是文件夹,会启用一对多机制'), self).exec_()
                shpPathList = checkShpList(selectShpCbText)
                tifPathList = [ tifPathList[0] for _ in range(len(shpPathList)) ]
                if self.CDRb.isChecked():
                    tifPathListII = [ tifPathListII[0] for _ in range(len(shpPathList)) ]
        else:
            if tifIsDir:
                # 情况3 矢量是文件 影像是文件夹
                MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('影像和矢量一个是文件一个是文件夹,会启用一对多机制'), self).exec_()
                shpPathSingle = PROJECT.mapLayersByName(self.selectShpCb.currentText())[0].source()
                tifPathList,tifPathListII = checkFileListByList(tifPathList,selectTifIICbText,post='.tif')
                shpPathList = [ shpPathSingle for _ in range(len(tifPathList))]
            else:
                # 情况4 都是文件
                shpPathList = [PROJECT.mapLayersByName(self.selectShpCb.currentText())[0].source()]

        if tifPathList == []:
            MessageBox(self.yoyiTrs._translate('警告'), f"{self.yoyiTrs._translate('没有有效影像')} {self.yoyiTrs._translate('请检查波段数量大于3,数据类型为Uint8')}", self).exec_()
            return
        
        if shpPathList == []:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('没有有效矢量'), self).exec_()
            return
        
        self.tifPathList = tifPathList
        self.shpPathList = shpPathList
        self.tifPathListII = tifPathListII
        
        if self.selectShpCb.count() == 0:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('没有有效矢量'), self).exec_()
            return
        
        if self.sampleNameLE.text().strip() == "":
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('请输入样本库名称'), self).exec_()
            return
        
        if self.sampleDescriptionLE.text().strip() == "":
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('请输入样本库描述'), self).exec_()
            return
        
        if self.sampleBuilderLE.text().strip() == "":
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('请输入样本库创建人'), self).exec_()
            return
        
    
        if self.selectShpFieldCheckBox.isChecked():
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('您勾选了使用字段生成数据集，请等待计算当前选择的字段唯一值列表'), self).exec_()
            
            currentFieldName = self.selectShpFieldCb.currentText()

            if self.CDRb.isChecked():
                extraFieldName = self.selectShpIIFieldCb.currentText()
            else:
                extraFieldName = None
            self.calUniqueValueThread = calFieldUniqueValuesRunClass(shpPathList=self.shpPathList,
                                                                    fieldName=currentFieldName,
                                                                    extraFieldName=extraFieldName)
            self.setEnabled(False)
            self.IndeterminateProgressBar.show()
            self.calUniqueValueThread.signal_over.connect(self.finishCalByCls)
            self.calUniqueValueThread.finished.connect(self.calUniqueValueThread.deleteLater)
            self.calUniqueValueThread.start()
        else:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('您没有勾选字段，请填写生成像素值和目标类别'), self).exec_()
            self.finishCalByCls(["",["目标"]])

    def finishCalByCls(self,params):
        self.setEnabled(True)
        self.IndeterminateProgressBar.setValue(0)
        self.IndeterminateProgressBar.hide()
        info,uniqueList = params
        if info != "":
            MessageBox(self.yoyiTrs._translate('警告'), info, self).exec_()
        else:
            if self.LCRb.isChecked():
                self.mode = "classify"
                self.filePre = "LC"
            elif self.ODRb.isChecked():
                self.mode = "objectDetection"
                self.filePre = "OD"
            elif self.CDRb.isChecked():
                self.mode = "classify"
                self.filePre = "CD"
            dialog = PixelClassifyMapWindowClass(nameList=uniqueList,
                                                 mode=self.mode,
                                                 hideBg=True,
                                                 needSelectType=True)
            dialog.exec()

            if dialog.completeStatus:
                pixelMap = dialog.pixelMap  # {'XX': 1}
                codeMap = dialog.codeMap # {'XX': '04'}
                jsonNameMap = dialog.jsonNameMap # {'XX' : '名称(04)'}

                diyPixelValue = int(list(pixelMap.values())[0])

                self.classDict = {}
                for name,pixelValue in pixelMap.items():
                    code = codeMap[name]
                    jsonName = jsonNameMap[name]
                    self.classDict[pixelValue] = f"{jsonName}"
                
                self.resDir = self.resLE.text()
                self.needTransRgb = self.transRGBCb.isChecked()
                self.overlap = 1 - (self.overlapSpinBox.value()/100)
                self.imgSize = self.imgSizeSpinBox.value()
                self.dropZero = self.dropZeroCheckBox.isChecked()
                
                if self.pngRb.isChecked():
                    self.generatePost = "png"
                elif self.jpgRb.isChecked():
                    self.generatePost = "jpg"
                elif self.tifRb.isChecked():
                    self.generatePost = "tif"

                if self.selectShpFieldCheckBox.isChecked():
                    self.shpField = self.selectShpFieldCb.currentText()
                    self.shpFieldII = self.selectShpIIFieldCb.currentText()
                    self.shpPixelMapping = pixelMap
                else:
                    self.shpField = None
                    self.shpFieldII = None
                    self.shpPixelMapping = None
                self.diyPixelValue = diyPixelValue

                if self.mosaicModeRb.isChecked():
                    self.mosaicShp = PROJECT.mapLayersByName(self.selectMosaicCb.currentText())[0].source()
                    self.mosaicShpImgidField = self.selectMosaicFieldCb.currentText()
                    self.imgIdTime = None
                else:
                    self.mosaicShp = None
                    self.mosaicShpImgidField = None
                    self.imgIdTime = self.ZhDatePicker.date.toString("yyyy-MM-dd")
                
                if self.mosaicModeRbII.isChecked():
                    self.mosaicShpII = PROJECT.mapLayersByName(self.selectMosaicCbII.currentText())[0].source()
                    self.mosaicShpImgidFieldII = self.selectMosaicFieldCbII.currentText()
                    self.imgIdTimeII = None
                else:
                    self.mosaicShpII = None
                    self.mosaicShpImgidFieldII = None
                    self.imgIdTimeII = self.ZhDatePickerII.date.toString("yyyy-MM-dd")
                
                self.initIndex = self.initIndexSpinBox.value()
                self.sampleName = self.sampleNameLE.text()
                self.sampleDescription = self.sampleDescriptionLE.text()
                self.sampleBuilder = self.sampleBuilderLE.text()
                self.imageAreaId = None
                self.isObb = self.isObbCheckBox.isChecked()
                self.clipMinAreaPer = self.clipMinAreaPerSpinBox.value()/100

                for name,code in codeMap.items():
                    self.filePre += f"_{code}"

                dialog.deleteLater()
                self.close()
        

                



