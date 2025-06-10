import os
import os.path as osp
from requests import get
from ui.settingWindow import Ui_Frame

from PyQt5.QtWidgets import QFrame, QWidget,QMainWindow
from PyQt5.QtGui import QIcon,QColor,QDesktopServices
from PyQt5.QtCore import QUrl,QCoreApplication

from qfluentwidgets import Flyout,setTheme,setThemeColor,Theme,ColorPickerButton,MessageBox
from qfluentwidgets import FluentIcon as FIF

from yoyiUtils.qtTriggeredCommon import qtTriggeredCommonDialog
from yoyiUtils.yoyiTranslate import yoyiTrans

from appConfig import yoyiSetting,ROOT_PATH
import yoyirs_rc

class SettingWidgetWindowClass(Ui_Frame,QFrame):
    def __init__(self,parent=None,mode='common'):
        super(SettingWidgetWindowClass, self).__init__(parent)
        self.parentWindow = parent
        self.setupUi(self)
        self.setObjectName("Widget_Setting")

        self.colorButton = ColorPickerButton(QColor(yoyiSetting().configSettingReader.value('windowColor', type=str)),
                                             '主题颜色选择', self, enableAlpha=True)
        self.colorButton.setMinimumWidth(300)
        self.colorButton.colorChanged.connect(self.updateWindowColor)
        self.horizontalLayout_2.addWidget(self.colorButton)
        # theme combobox
        self.themeCBox.addItems(["明亮", "暗黑"])
        
        # language 
        self.languageCBox.addItems(["简体中文","English"])

        # snap
        self.snapTypeCBox.addItems(["顶点","线段","顶点与线段"])

        # 是否触发 connect
        self.isConnected = True
        self.CardWidget_Color.hide()
        self.CardWidget_16.hide() #preload的东西

        self.initUI()
        self.refreshUI()
        self.connectFunc()


    def initUI(self):
        # ICON
        self.themePb.setIcon(FIF.BRUSH)
        self.languagePb.setIcon(FIF.LANGUAGE)
        self.themeColorPb.setIcon(FIF.PALETTE)
        
        self.simpleAutoPb.setIcon(QIcon(':/img/resources/shpProcess/shp_simply.png'))
        self.rectangleSettingPb.setIcon(QIcon(':/img/resources/shpProcess/shp_simply.png'))
        self.moveSettingPb.setIcon(QIcon(':/img/resources/gis/shp_move.png'))
        self.MinMovementDistancePb.setIcon(QIcon(':/img/resources/gis/shp_move.png'))
        self.AutoCompletePb.setIcon(QIcon(':/img/resources/topologic.svg'))
        self.AllowSnapPb.setIcon(QIcon(':/img/resources/snap.svg'))
        self.SnapTypePb.setIcon(QIcon(':/img/resources/snap.svg'))
        self.SnapDistancePb.setIcon(QIcon(':/img/resources/snap.svg'))
        self.StreamTolerancePb.setIcon(QIcon(':/img/resources/gis/shp_line2Poly.png'))
        self.PreloadModePb.setIcon(FIF.CLOUD_DOWNLOAD)

        self.samIpPb.setIcon(FIF.LINK)
        self.localProjectPB.setIcon(FIF.DICTIONARY)
        self.aboutPb.setIcon(FIF.INFO)
        self.versionPb.setIcon(FIF.CERTIFICATE)
        self.changeLocalProjectPB.setIcon(FIF.MORE)
    
    def refreshUI(self):
        self.isConnected = False
        self.themeCBox.setCurrentIndex(yoyiSetting().configSettingReader.value('windowStyle',type=int))
        # language
        language = yoyiSetting().configSettingReader.value('appLanguage',type=str)
        if language == "Ch":
            self.languageCBox.setCurrentIndex(0)
        else:
            self.languageCBox.setCurrentIndex(1)
        # Labeling
        self.simplyFeatureSwitchButton.setChecked(yoyiSetting().configSettingReader.value('simpleFeature',type=bool))
        self.rectangleMapToolSwitchButton.setChecked(yoyiSetting().configSettingReader.value('horizontalRectangle',type=bool))
        self.selectionMapToolSwitchButton.setChecked(yoyiSetting().configSettingReader.value('allowMoveFeature',type=bool))
        self.minMoveDistanceSpinBox.setValue(yoyiSetting().configSettingReader.value('minMovementDistance',type=int))
        self.autoCompleteMapToolSwitchButton.setChecked(yoyiSetting().configSettingReader.value('autoComplete',type=bool))
        self.allowSnapSwitchButton.setChecked(yoyiSetting().configSettingReader.value('allowSnap',type=bool))
        self.snapTypeCBox.setCurrentIndex(yoyiSetting().configSettingReader.value('snapType',type=int))
        self.snapDistanceSpinBox.setValue(yoyiSetting().configSettingReader.value('snapDistance',type=int))
        self.streamToleranceSpinBox.setValue(yoyiSetting().configSettingReader.value('streamTolerance',type=int))
        self.preloadModeSwitchButton.setChecked(yoyiSetting().configSettingReader.value('preloadMode',type=bool))
        # IP
        self.samLE.setText(yoyiSetting().configSettingReader.value('samIp',type=str))

        self.localProjectPathLE.setText(yoyiSetting().configSettingReader.value('localProject',type=str))

        # about
        currentVersionPath = osp.join(ROOT_PATH,"cv.dll")
        try:
            with open(currentVersionPath,'r',encoding='utf-8') as file:
                self.currentVersion = float(file.readline())
        except Exception as e:
            self.currentVersion = 0.0
        self.versionLabel.setText(f"{self.currentVersion}")

        self.isConnected = True
        
    
    def retranslateDiyUI(self):
        _translate = QCoreApplication.translate
        self.colorButton.setText(_translate("DIYDialog", "Theme Color Selection"))

        self.aboutLabel.setText(
            f"{_translate('Frame', '© All Rights Reserved')} {_translate('Frame', 'Chang Guang Satellite Technology CO.LTD')}"
        )

        self.themeCBox.setItemText(0,text=_translate("DIYDialog", "Light"))
        self.themeCBox.setItemText(1,text=_translate("DIYDialog", "Dark"))

        self.snapTypeCBox.setItemText(0,text=_translate("DIYDialog", "Vertex"))
        self.snapTypeCBox.setItemText(1,text=_translate("DIYDialog", "Segment"))
        self.snapTypeCBox.setItemText(2,text=_translate("DIYDialog", "VertexAndSegment"))

        self.versionLabel.setText(f"{self.currentVersion}")

    def connectFunc(self):
        self.themeCBox.currentIndexChanged.connect(self.updateThemeStyle)
        self.languageCBox.currentTextChanged.connect(self.updateLanguage)

        self.simplyFeatureSwitchButton.checkedChanged.connect(self.simplyChanged)
        self.rectangleMapToolSwitchButton.checkedChanged.connect(self.rectangleChanged)
        self.selectionMapToolSwitchButton.checkedChanged.connect(self.allowMoveChanged)
        self.minMoveDistanceSpinBox.valueChanged.connect(self.minMoveDistanceSpinBoxChanged)
        self.autoCompleteMapToolSwitchButton.checkedChanged.connect(self.autoCompleteChanged)
        self.allowSnapSwitchButton.checkedChanged.connect(self.allowSnapSwitchButtonChanged)
        self.snapTypeCBox.currentIndexChanged.connect(self.snapTypeCBoxChanged)
        self.snapDistanceSpinBox.valueChanged.connect(self.snapDistanceSpinBoxChanged)
        self.streamToleranceSpinBox.valueChanged.connect(self.streamToleranceSpinBoxChanged)
        self.preloadModeSwitchButton.checkedChanged.connect(self.preloadModeSwitchButtonChanged)

        self.samLE.editingFinished.connect(self.samLETextChanged)
        self.changeLocalProjectPB.clicked.connect(lambda : qtTriggeredCommonDialog().addFileDirTriggered(self.localProjectPathLE,preDir="C://"))
        self.localProjectPathLE.textChanged.connect(self.loaclProjectTextChanged)

        self.gotoWebPb.clicked.connect(lambda :QDesktopServices.openUrl(QUrl("http://10.10.103.18:8083/imgpdc/home")))
        self.checkUpdatePb.clicked.connect(self.checkUpdateClicked)
        self.restorePb.clicked.connect(self.restorePbClicked)

    def updateWindowColor(self):
        newColor : QColor = self.colorButton.color
        yoyiSetting().changeSetting('windowColor',newColor.name())
        setThemeColor(newColor.name())

    def updateThemeStyle(self):
        if self.isConnected:
            index = self.themeCBox.currentIndex()
            yoyiSetting().changeSetting("windowStyle",index)
            if index == 1:
                self.parentWindow.changeWindowStyle(True)
            else:
                self.parentWindow.changeWindowStyle(False)
    
    def updateLanguage(self):
        if self.isConnected:
            text = self.languageCBox.currentText()
            if text == "简体中文":
                yoyiSetting().changeSetting("appLanguage","Ch")
            else:
                yoyiSetting().changeSetting("appLanguage","En")
            
            self.parentWindow.changeWindowLanguage()
        
    def simplyChanged(self):
        if self.isConnected:
            yoyiSetting().changeSetting('simpleFeature', self.simplyFeatureSwitchButton.isChecked())

    def rectangleChanged(self):
        if self.isConnected:
            yoyiSetting().changeSetting('horizontalRectangle', self.rectangleMapToolSwitchButton.isChecked())
    
    def allowMoveChanged(self):
        if self.isConnected:
            yoyiSetting().changeSetting('allowMoveFeature', self.selectionMapToolSwitchButton.isChecked())
    
    def minMoveDistanceSpinBoxChanged(self):
        if self.isConnected:
            yoyiSetting().changeSetting('minMovementDistance',self.minMoveDistanceSpinBox.value())
    
    def autoCompleteChanged(self):
        if self.isConnected:
            yoyiSetting().changeSetting('autoComplete', self.autoCompleteMapToolSwitchButton.isChecked()) 
    
    def allowSnapSwitchButtonChanged(self):
        if self.isConnected:
            yoyiSetting().changeSetting('allowSnap', self.allowSnapSwitchButton.isChecked()) 
    
    def snapTypeCBoxChanged(self):
        if self.isConnected:
            yoyiSetting().changeSetting('snapType',self.snapTypeCBox.currentIndex())
    
    def snapDistanceSpinBoxChanged(self):
        if self.isConnected:
            yoyiSetting().changeSetting('snapDistance',self.snapDistanceSpinBox.value())
    
    def streamToleranceSpinBoxChanged(self):
        if self.isConnected:
            yoyiSetting().changeSetting('streamTolerance',self.streamToleranceSpinBox.value())
    
    def preloadModeSwitchButtonChanged(self):
        if self.isConnected:
            yoyiSetting().changeSetting('preloadMode',self.preloadModeSwitchButton.isChecked())
    
    def samLETextChanged(self):
        if self.isConnected:
            yoyiSetting().changeSetting('samIp', self.samLE.text())

    def loaclProjectTextChanged(self):
        if self.isConnected:
            yoyiSetting().changeSetting('localProject', self.localProjectPathLE.text())

    def checkUpdateClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans

        newVersion = 0
        if newVersion > self.currentVersion:
            w = MessageBox(yoyiTrs._translate("检查更新"), 
                           yoyiTrs._translate("发现新版本，是否更新？更新时将会关闭所有有关应用程序，请注意！！！"), 
                           self.parentWindow)
            w.yesButton.setText(yoyiTrs._translate('确认'))
            w.cancelButton.setText(yoyiTrs._translate('取消'))
            if w.exec():
                self.parentWindow.closeAppForUpdate()
        else:
            MessageBox(yoyiTrs._translate("检查更新"), yoyiTrs._translate("您当前版本已经是最新版本!"), self.parentWindow).exec_()

    def restorePbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        w = MessageBox(
            yoyiTrs._translate('恢复默认设置'),
            yoyiTrs._translate('您确定要恢复默认设置吗？'),
            self.parentWindow
        )
        w.yesButton.setText(yoyiTrs._translate('确认'))
        w.cancelButton.setText(yoyiTrs._translate('取消'))

        if w.exec():
            yoyiSetting().reStoreSetting()
            #self.parentWindow.homeInterface.saveDirLE.setText(yoyiSetting().configSettingReader.value('saveDir', type=str))
            self.refreshUI()
            self.updateThemeStyle()
            self.colorButton.setColor(QColor(yoyiSetting().configSettingReader.value('windowColor', type=str)))



