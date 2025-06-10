import os
import os.path as osp
from appConfig import *

from ui.draw_dialog.attrEditDialog import Ui_attrEditDialog
from PyQt5.QtCore import QVariant,QStringListModel,Qt
from PyQt5 import QtCore
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QVBoxLayout,QHBoxLayout,QDesktopWidget,QDialog,QColorDialog,QMessageBox,QSizePolicy,\
    QProgressBar,QDockWidget,QFileDialog,QHBoxLayout,QApplication,QLineEdit,QButtonGroup
from qgis.core import QgsFeatureRenderer,QgsRectangle,QgsFeature,QgsFillSymbol,QgsRasterLayer,QgsProject,Qgis,QgsColorRampShader\
    ,QgsPalettedRasterRenderer,QgsVectorLayer,QgsField,QgsVectorFileWriter,QgsTextFormat,\
    QgsPalLayerSettings,QgsVectorLayerSimpleLabeling,QgsSimpleLineSymbolLayer,QgsSingleSymbolRenderer,QgsGeometry
from qfluentwidgets import StrongBodyLabel,BodyLabel,SpinBox,MessageBox,LineEdit,PrimaryPushButton,FlowLayout,setFont,\
    PillPushButton

from widgets.draw_dialog_selectCateWindow import selectClsfyDialogClass,selectDetectionDialogClass

from yoyiUtils.custom_maptool import *
from yoyiUtils.yoyiRenderProp import yoyiShpPropClass,createShpLabel
from yoyiUtils.yoyiFile import readYamlToDict,checkTifList
from yoyiUtils.yoyiSamRequest import samWeber,postGisWeber
from yoyiUtils.yoyiDefault import huaweiCMClass

from appConfig import yoyiSetting,AttrType
PROJECT = QgsProject.instance()


def getAttrByDefault(remark1PreAttr,remark2PreAttr,remark3PreAttr,
                    remark1Type,remark2Type,remark3Type,
                    remark1List,remark2List,remark3List,
                    remark2String,remark3String):
    
    if remark1Type == AttrType.String:
        if remark1PreAttr:
            remark1Content = str(remark1PreAttr)
        else:
            remark1Content = ""
    elif remark1Type == AttrType.List:
        if remark1PreAttr and remark1PreAttr in remark1List:
            remark1Content = remark1PreAttr
        else:
            remark1Content = remark1List[0]
    elif remark1Type == AttrType.Int:
        if remark1PreAttr:
            try:
                remark1Content = int(remark1PreAttr)
            except Exception as e:
                remark1Content = 0
        else:
            remark1Content = 0
    
    remark2Content = None
    if remark2String:
        if remark2Type == AttrType.String:
            if remark2PreAttr:
                remark2Content = str(remark2PreAttr)
            else:
                remark2Content = ""
        elif remark2Type == AttrType.List:
            if remark2PreAttr and remark2PreAttr in remark2List:
                remark2Content = remark2PreAttr
            else:
                remark2Content = remark2List[0]
        elif remark2Type == AttrType.Int:
            if remark2PreAttr:
                try:
                    remark2Content = int(remark2PreAttr)
                except Exception as e:
                    remark2Content = 0
            else:
                remark2Content = 0
    
    remark3Content = None
    if remark3String:
        if remark3Type == AttrType.String:
            if remark3PreAttr:
                remark3Content = str(remark3PreAttr)
            else:
                remark3Content = ""
        elif remark3Type == AttrType.List:
            if remark3PreAttr and remark3PreAttr in remark3List:
                remark3Content = remark3PreAttr
            else:
                remark3Content = remark3List[0]
        elif remark3Type == AttrType.Int:
            if remark3PreAttr:
                try:
                    remark3Content = int(remark3PreAttr)
                except Exception as e:
                    remark3Content = 0
            else:
                remark3Content = 0

    return remark1Content,remark2Content,remark3Content
        


class WebAttrEditDialogClass(Ui_attrEditDialog,QDialog):
    def __init__(self,remark1String,remark1Type,remark1List,remark1PreAttr=None,
                 remark2String=None,remark2Type=None,remark2List=None,remark2PreAttr=None,
                 remark3String=None,remark3Type=None,remark3List=None,remark3PreAttr=None, parent=None):
        super(WebAttrEditDialogClass, self).__init__(parent)
        self.setupUi(self)
        self.parentWindow = parent

        self.remark1PreAttr = self.parentWindow.remark1PreAttr
        self.remark2PreAttr = self.parentWindow.remark2PreAttr
        self.remark3PreAttr = self.parentWindow.remark3PreAttr

        self.remark1String = remark1String
        self.remark1Type = remark1Type
        self.remark1List = remark1List
        if remark1PreAttr:
            self.remark1PreAttr = remark1PreAttr

        self.remark2String = remark2String
        self.remark2Type = remark2Type
        self.remark2List = remark2List
        if remark2PreAttr:
            self.remark2PreAttr = remark2PreAttr

        self.remark3String = remark3String
        self.remark3Type = remark3Type
        self.remark3List = remark3List
        if remark3PreAttr:
            self.remark3PreAttr = remark3PreAttr

        self.initMember()
        self.initUI()
        self.connectFunc()
    
    def initMember(self):
        self.remark1Attr = None
        self.remark2Attr = None
        self.remark3Attr = None
    
    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)

        # 左侧标签的 尺寸调整
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        # 1 remark1 
        self.R1Layout = FlowLayout()
        self.R1Layout.setObjectName(f"tempLayout_remark1")

        self.R1Label = BodyLabel(self.ScrollAreaWidget)
        self.R1Label.setText(f"{self.remark1String}: ")
        self.R1Label.setSizePolicy(sizePolicy)
        self.R1Layout.addWidget(self.R1Label)
        # 1.1 判断remark1 是哪种类型
        if self.remark1Type == AttrType.String:
            self.R1ContentWidget = LineEdit(self.ScrollAreaWidget)
            if self.remark1PreAttr:
                self.R1ContentWidget.setText(self.remark1PreAttr)
            self.R1Layout.addWidget(self.R1ContentWidget)
        elif self.remark1Type == AttrType.List:
            self.R1ContentWidget = QButtonGroup(self.ScrollAreaWidget)
            for index,content in enumerate(self.remark1List):
                tempR1Pb = PillPushButton(f'{content}',parent=self.ScrollAreaWidget)
                if self.remark1PreAttr == content:
                    tempR1Pb.setChecked(True)
                elif self.remark1PreAttr is None and index == 0:
                    tempR1Pb.setChecked(True)
                self.R1ContentWidget.addButton(tempR1Pb)
                self.R1Layout.addWidget(tempR1Pb)
        elif self.remark1Type == AttrType.Int:
            self.R1ContentWidget = SpinBox(self.ScrollAreaWidget)
            self.R1ContentWidget.setMaximum(999999)
            if self.remark1PreAttr:
                try:
                    self.R1ContentWidget.setValue(int(self.remark1PreAttr))
                except Exception as e:
                    pass
            self.R1Layout.addWidget(self.R1ContentWidget)  
        self.verticalLayout_2.insertLayout(0,self.R1Layout)

        # 2 remark2 
        if self.remark2String:
            self.R2Layout = FlowLayout()
            self.R2Layout.setObjectName(f"tempLayout_remark2")

            self.R2Label = BodyLabel(self.ScrollAreaWidget)
            self.R2Label.setText(f"{self.remark2String}: ")
            self.R2Label.setSizePolicy(sizePolicy)
            self.R2Layout.addWidget(self.R2Label)
            # 1.1 判断remark2 是哪种类型
            if self.remark2Type == AttrType.String:
                self.R2ContentWidget = LineEdit(self.ScrollAreaWidget)
                if self.remark2PreAttr:
                    self.R2ContentWidget.setText(self.remark2PreAttr)
                self.R2Layout.addWidget(self.R2ContentWidget)
            elif self.remark2Type == AttrType.List:
                self.R2ContentWidget = QButtonGroup(self.ScrollAreaWidget)
                for index,content in enumerate(self.remark2List):
                    tempR2Pb = PillPushButton(f'{content}',parent=self.ScrollAreaWidget)
                    if self.remark2PreAttr == content:
                        tempR2Pb.setChecked(True)
                    elif self.remark2PreAttr is None and index == 1:
                        tempR2Pb.setChecked(True)
                    self.R2ContentWidget.addButton(tempR2Pb)
                    self.R2Layout.addWidget(tempR2Pb)
            elif self.remark2Type == AttrType.Int:
                self.R2ContentWidget = SpinBox(self.ScrollAreaWidget)
                if self.remark2PreAttr:
                    try:
                        self.R2ContentWidget.setValue(int(self.remark2PreAttr))
                    except Exception as e:
                        pass
                self.R2Layout.addWidget(self.R2ContentWidget)  
            self.verticalLayout_2.insertLayout(1,self.R2Layout)
    
        # 3 remark3
        if self.remark3String:
            self.R3Layout = FlowLayout()
            self.R3Layout.setObjectName(f"tempLayout_remark1")

            self.R3Label = BodyLabel(self.ScrollAreaWidget)
            self.R3Label.setText(f"{self.remark3String}: ")
            self.R3Label.setSizePolicy(sizePolicy)
            self.R3Layout.addWidget(self.R3Label)
            # 1.1 判断remark2 是哪种类型
            if self.remark3Type == AttrType.String:
                self.R3ContentWidget = LineEdit(self.ScrollAreaWidget)
                if self.remark3PreAttr:
                    self.R3ContentWidget.setText(self.remark3PreAttr)
                self.R3Layout.addWidget(self.R3ContentWidget)
            elif self.remark3Type == AttrType.List:
                self.R3ContentWidget = QButtonGroup(self.ScrollAreaWidget)
                for index,content in enumerate(self.remark3List):
                    tempR3Pb = PillPushButton(f'{content}',parent=self.ScrollAreaWidget)
                    if self.remark3PreAttr == content:
                        tempR3Pb.setChecked(True)
                    elif self.remark3PreAttr is None and index == 2:
                        tempR3Pb.setChecked(True)
                    self.R3ContentWidget.addButton(tempR3Pb)
                    self.R3Layout.addWidget(tempR3Pb)
            elif self.remark3Type == AttrType.Int:
                self.R3ContentWidget = SpinBox(self.ScrollAreaWidget)
                if self.remark3PreAttr:
                    try:
                        self.R3ContentWidget.setValue(int(self.remark3PreAttr))
                    except Exception as e:
                        pass
                self.R3Layout.addWidget(self.R3ContentWidget)  
            self.verticalLayout_2.insertLayout(2,self.R3Layout)
    
    def connectFunc(self):
        self.okPushButton.clicked.connect(self.okPushButtonClicked)
        self.cancelPushButton.clicked.connect(self.close)

    def okPushButtonClicked(self):
        if self.remark1Type == AttrType.String:
            remark1Attr = self.R1ContentWidget.text()
        elif self.remark1Type == AttrType.List:
            if not self.R1ContentWidget.checkedButton():
                MessageBox('警告', f"{self.remark1String} 没有选中！", self).exec_()
                return
            remark1Attr = self.R1ContentWidget.checkedButton().text()
        elif self.remark1Type == AttrType.Int:
            remark1Attr = self.R1ContentWidget.value()
        
        if self.remark2String:
            if self.remark2Type == AttrType.String:
                remark2Attr = self.R2ContentWidget.text()
            elif self.remark2Type == AttrType.List:
                if not self.R2ContentWidget.checkedButton():
                    MessageBox('警告', f"{self.remark2String} 没有选中！", self).exec_()
                    return
                remark2Attr = self.R2ContentWidget.checkedButton().text()
            elif self.remark2Type == AttrType.Int:
                remark2Attr = self.R2ContentWidget.value()
        else:
            remark2Attr = ""
        
        if self.remark3String:
            if self.remark3Type == AttrType.String:
                remark3Attr = self.R3ContentWidget.text()
            elif self.remark3Type == AttrType.List:
                if not self.R3ContentWidget.checkedButton():
                    MessageBox('警告', f"{self.remark3String} 没有选中！", self).exec_()
                    return
                remark3Attr = self.R3ContentWidget.checkedButton().text()
            elif self.remark3Type == AttrType.Int:
                remark3Attr = self.R3ContentWidget.value()
        else:
            remark3Attr = ""
        
        self.remark1Attr = remark1Attr
        self.remark2Attr = remark2Attr
        self.remark3Attr = remark3Attr
        self.parentWindow.remark1PreAttr = remark1Attr
        self.parentWindow.remark2PreAttr = remark2Attr
        self.parentWindow.remark3PreAttr = remark3Attr
        self.close()


