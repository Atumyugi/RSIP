
import os
import os.path as osp
from appConfig import *

from ui.draw_dialog.attrEditDialog import Ui_attrEditDialog
from PyQt5.QtCore import QVariant,QStringListModel,Qt
from PyQt5 import QtCore
from PyQt5.QtGui import QColor,QIntValidator,QDoubleValidator
from PyQt5.QtWidgets import QVBoxLayout,QHBoxLayout,QDateEdit,QDialog,QColorDialog,QMessageBox,QSizePolicy,QProgressBar,QDockWidget,QFileDialog,QHBoxLayout,QApplication
from qgis.core import QgsFeatureRenderer,QgsRectangle,QgsFeature,QgsFillSymbol,QgsRasterLayer,QgsProject,Qgis,QgsColorRampShader\
    ,QgsPalettedRasterRenderer,QgsVectorLayer,QgsField,QgsVectorFileWriter,QgsTextFormat,\
    QgsPalLayerSettings,QgsVectorLayerSimpleLabeling,QgsSimpleLineSymbolLayer,QgsSingleSymbolRenderer,QgsGeometry
from qfluentwidgets import ZhDatePicker,BodyLabel,SpinBox,MessageBox,LineEdit,PrimaryPushButton,setFont

from widgets.draw_dialog_selectCateWindow import selectClsfyDialogClass,selectDetectionDialogClass

from yoyiUtils.custom_maptool import *
from yoyiUtils.yoyiRenderProp import yoyiShpPropClass,createShpLabel
from yoyiUtils.yoyiFile import readYamlToDict,checkTifList
from yoyiUtils.yoyiTranslate import yoyiTrans
from appConfig import yoyiSetting
PROJECT = QgsProject.instance()

class AttrEditDialog(Ui_attrEditDialog,QDialog):
    def __init__(self,vectorLayer:QgsVectorLayer,yoyiTrs:yoyiTrans, parent=None):
        super(AttrEditDialog, self).__init__(parent)
        self.setupUi(self)

        self.vectorLayer = vectorLayer
        self.nameList = []
        self.fieldTypeList = []
        self.fieldLengthList = []
        for field in vectorLayer.fields():
            #print(f"name: {field.name()}, type: {field.typeName()} {field.length()}")
            # Integer64 String Real Date
            self.nameList.append(field.name())
            self.fieldTypeList.append(field.typeName())
            self.fieldLengthList.append(field.length())
        self.yoyiTrs = yoyiTrs
        
        self.initUI()
        self.connectFunc()

    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)

        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)

        self.lineEditList = []
        for index,name in enumerate(self.nameList):
            tempLayout = QHBoxLayout()
            tempLayout.setObjectName(f"tempLayout_{name}")
            
            tempSpinBoxLabel = BodyLabel(self.ScrollAreaWidget)
            tempSpinBoxLabel.setText(name)
            tempSpinBoxLabel.setSizePolicy(sizePolicy)
            tempLayout.addWidget(tempSpinBoxLabel)
            
            if "nteger" in self.fieldTypeList[index]:
                tempAttributeLineEdit = LineEdit(self.ScrollAreaWidget)
                tempAttributeLineEdit.setValidator(QIntValidator())
                tempAttributeLineEdit.setMaxLength(self.fieldLengthList[index])
            elif "Real" in self.fieldTypeList[index] or "ouble" in self.fieldTypeList[index]:
                tempAttributeLineEdit = LineEdit(self.ScrollAreaWidget)
                tempAttributeLineEdit.setValidator(QDoubleValidator())
                tempAttributeLineEdit.setMaxLength(self.fieldLengthList[index])
            elif "Date" in self.fieldTypeList[index]:
                tempAttributeLineEdit = ZhDatePicker(self.ScrollAreaWidget)
                tempAttributeLineEdit.text()
            else:
                tempAttributeLineEdit = LineEdit(self.ScrollAreaWidget)
                tempAttributeLineEdit.setMaxLength(self.fieldLengthList[index])
            tempAttributeLineEdit.setProperty("index",index)
            tempAttributeLineEdit.setProperty("name",name)
            tempLayout.addWidget(tempAttributeLineEdit)

            self.verticalLayout_2.insertLayout(index,tempLayout)
            self.lineEditList.append(tempAttributeLineEdit)
    
    def connectFunc(self):
        self.okPushButton.clicked.connect(self.okPushButtonClicked)
        self.cancelPushButton.clicked.connect(self.close)
    
    def okPushButtonClicked(self):
        
        newAttrs = {}
        for lineEidt in self.lineEditList:

            if type(lineEidt) == ZhDatePicker:
                newAttrs[lineEidt.property("index")] = lineEidt.getDate().toString("yyyy/MM/dd")
            else:
                newAttrs[lineEidt.property("index")] = lineEidt.text()
        
        self.parent().editStack.beginMacro("changeAttrs")
        for featureId in self.vectorLayer.selectedFeatureIds():
            self.vectorLayer.changeAttributeValues(featureId,newAttrs)
        self.parent().editStack.endMacro()
        self.parent().mapCanvas.refresh()
        self.parent().updateShpUndoRedoButton()

        self.close()
