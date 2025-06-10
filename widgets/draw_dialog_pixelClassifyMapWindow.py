
import os
import os.path as osp
from appConfig import *

from ui.draw_dialog.pixelClassifyMapDialog import Ui_pixelClassifyMapDialog
from PyQt5.QtCore import QVariant,QStringListModel,Qt
from PyQt5 import QtCore
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QVBoxLayout,QHBoxLayout,QDesktopWidget,QDialog,QColorDialog,QMessageBox,QSizePolicy,QProgressBar,QDockWidget,QFileDialog,QHBoxLayout,QApplication
from qgis.core import QgsFeatureRenderer,QgsRectangle,QgsFeature,QgsFillSymbol,QgsRasterLayer,QgsProject,Qgis,QgsColorRampShader\
    ,QgsPalettedRasterRenderer,QgsVectorLayer,QgsField,QgsVectorFileWriter,QgsTextFormat,\
    QgsPalLayerSettings,QgsVectorLayerSimpleLabeling,QgsSimpleLineSymbolLayer,QgsSingleSymbolRenderer,QgsGeometry
from qfluentwidgets import StrongBodyLabel,BodyLabel,SpinBox,MessageBox,LineEdit,PrimaryPushButton,setFont

from widgets.draw_dialog_selectCateWindow import selectClsfyDialogClass,selectDetectionDialogClass

from yoyiUtils.custom_maptool import *
from yoyiUtils.yoyiRenderProp import yoyiShpPropClass,createShpLabel
from yoyiUtils.yoyiFile import readYamlToDict,checkTifList

from appConfig import yoyiSetting
PROJECT = QgsProject.instance()

class PixelClassifyMapWindowClass(Ui_pixelClassifyMapDialog,QDialog):
    def __init__(self,nameList,mode="classify",hideBg=False,needSelectType=False, parent=None):
        super(PixelClassifyMapWindowClass, self).__init__(parent)
        self.setupUi(self)
        self.nameList = nameList
        self.mode = mode
        self.hideBg = hideBg
        self.needSelectType = needSelectType
        self.initUI()
        self.connectFunc()
    
    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        self.completeStatus = False
        self.pixelMap = {}
        self.nodataValue = 0

        self.spinBoxDict: dict[str,SpinBox] = {}

        self.verticalScrollLayout = QVBoxLayout(self.ScrollAreaWidget)
        self.verticalScrollLayout.setObjectName("verticalScrollLayout")

        self.buttonLabelDict = {}

        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        if self.mode == "classify" or self.mode == "objectDetection":
            for index,name in enumerate(self.nameList):
                name = str(name)
                tempLayout = QHBoxLayout()
                tempLayout.setObjectName(f"tempLayout_{index}")

                tempSpinBoxLabel = BodyLabel(self.ScrollAreaWidget)
                tempSpinBoxLabel.setText("选择像素值：")
                tempSpinBoxLabel.setSizePolicy(sizePolicy)
                tempLayout.addWidget(tempSpinBoxLabel)

                tempSpinBox = SpinBox(self.ScrollAreaWidget)
                tempSpinBox.setObjectName(f"tempSpinBox_{index}")
                tempSpinBox.setMinimum(-65536)
                tempSpinBox.setMaximum(65536)
                tempSpinBox.setValue(index+1 if self.mode=="classify" else index)
                tempLayout.addWidget(tempSpinBox)

                if self.needSelectType:
                    
                    tempSelectTypePb = PrimaryPushButton(self.ScrollAreaWidget)
                    tempSelectTypePb.setText("选择类别")
                    tempSelectTypePb.setObjectName(f"tempButtonname_{name}")
                    tempSelectTypePb.clicked.connect(self.selectTypePbClicked)
                    tempLayout.addWidget(tempSelectTypePb)

                    tempSelectedTypeLE = LineEdit(self.ScrollAreaWidget)
                    tempSelectedTypeLE.setReadOnly(True)
                    tempLayout.addWidget(tempSelectedTypeLE)
                    self.buttonLabelDict[name] = tempSelectedTypeLE

                tempClassifyNameTipLabel = BodyLabel(self.ScrollAreaWidget)
                tempClassifyNameTipLabel.setText("当前名称：")
                tempClassifyNameTipLabel.setSizePolicy(sizePolicy)
                tempLayout.addWidget(tempClassifyNameTipLabel)

                tempClassifyNameLabel = StrongBodyLabel(self.ScrollAreaWidget)
                tempClassifyNameLabel.setObjectName(f"tempClassifyNameLabel_{index}")
                tempClassifyNameLabel.setText(name)
                tempLayout.addWidget(tempClassifyNameLabel)

                
                self.verticalLayout_2.insertLayout(index,tempLayout)
                self.spinBoxDict[name] = tempSpinBox
        elif self.mode == "changeDetection":
            if len(self.nameList) < 2:
                tempLayout = QHBoxLayout()
                tempLayout.setObjectName(f"tempLayout_{0}")
                tempSpinBox = SpinBox(self.ScrollAreaWidget)
                tempSpinBox.setObjectName(f"tempSpinBox_{0}")
                tempSpinBox.setMinimum(-65536)
                tempSpinBox.setMaximum(65536)
                tempSpinBox.setValue(0)
                tempLayout.addWidget(tempSpinBox)

                tempClassifyNameLabel = BodyLabel(self.ScrollAreaWidget)
                tempClassifyNameLabel.setObjectName(f"tempClassifyNameLabel_{0}")
                tempClassifyNameLabel.setText(self.nameList[0])
                tempLayout.addWidget(tempClassifyNameLabel)
                self.verticalLayout_2.insertLayout(0,tempLayout)
                self.spinBoxDict[self.nameList[0]] = tempSpinBox
            else:
                index = 0 
                for namePre in self.nameList:
                    for namePost in self.nameList:
                        if namePost != namePre:
                            tempLayout = QHBoxLayout()
                            tempLayout.setObjectName(f"tempLayout_{index}")
                            tempSpinBox = SpinBox(self.ScrollAreaWidget)
                            tempSpinBox.setObjectName(f"tempSpinBox_{index}")
                            tempSpinBox.setMinimum(-65536)
                            tempSpinBox.setMaximum(65536)
                            tempSpinBox.setValue(0)
                            tempLayout.addWidget(tempSpinBox)

                            tempClassifyNameLabel = BodyLabel(self.ScrollAreaWidget)
                            tempClassifyNameLabel.setObjectName(f"tempClassifyNameLabel_{index}")
                            tempClassifyNameLabel.setText(namePre+STRING_Right+namePost)
                            tempLayout.addWidget(tempClassifyNameLabel)
                            self.verticalLayout_2.insertLayout(index,tempLayout)
                            self.spinBoxDict[namePre+STRING_Right+namePost] = tempSpinBox
                            index += 1

        if self.hideBg:
            self.bgClassifyName.setVisible(False)
            self.bgSpinBox.setVisible(False)
    def connectFunc(self):
        self.okPushButton.clicked.connect(self.okPushButtonClicked)
        self.cancelPushButton.clicked.connect(self.close)
    
    def selectTypePbClicked(self):
        button = self.sender()
        tempLe = self.buttonLabelDict[button.objectName().split("_")[-1]]
        if self.mode == "classify":
            dialog = selectClsfyDialogClass(self)
        else:
            dialog = selectDetectionDialogClass(self)
        dialog.exec()
        if dialog.resName and dialog.resCode:
            tempLe.setText(f"{dialog.resName}:{dialog.resCode}")
        dialog.deleteLater()
    
    def okPushButtonClicked(self):
        tempMap = {}
        tempNodataValue = 0
        for name,spinBoxTemp in self.spinBoxDict.items():
            if spinBoxTemp.value() not in tempMap.values():
                tempMap[name] = spinBoxTemp.value()
            else:
                MessageBox('警告', "像素值出现重复！！！", self).exec_()
                return
        
        if not self.hideBg:
            if self.bgSpinBox.value() not in tempMap.values():
                tempNodataValue = self.bgSpinBox.value()
            else:
                MessageBox('警告', "背景像素值与映射表重复！！！", self).exec_()
                return
        
        if len(self.buttonLabelDict) > 0:
            resCodeMap = {}
            resJsonNameMap = {}
            for name,leTemp in self.buttonLabelDict.items():
                tempName,tempCode = leTemp.text().split(":")
                if tempCode not in resCodeMap.values():
                    resCodeMap[name] = tempCode
                    resJsonNameMap[name] = f"{tempName}({tempCode})"
                else:
                    MessageBox('警告','唯一编码出现重复，请修改冒号后面的编码',self).exec()
                    return 
        else:
            resCodeMap = {}
            resJsonNameMap = {}

        self.pixelMap = tempMap
        self.codeMap = resCodeMap
        self.jsonNameMap = resJsonNameMap
        self.nodataValue = tempNodataValue
        self.completeStatus = True
        self.close()