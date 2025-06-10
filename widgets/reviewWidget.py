import os
import os.path as osp

from ui.reviewWorkWindow import Ui_reviewWorkWindow

from PyQt5.QtCore import QVariant,QStringListModel,Qt
from PyQt5 import QtCore
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QAbstractItemView,QMenu, QAction,QUndoStack,QMainWindow,QDesktopWidget,QDialog,QColorDialog,QMessageBox,QSizePolicy,QProgressBar,QDockWidget,QFileDialog,QHBoxLayout,QApplication
from qgis.core import QgsRectangle,QgsFeature,QgsFillSymbol,QgsRasterLayer,QgsProject,Qgis,QgsColorRampShader\
    ,QgsPalettedRasterRenderer,QgsVectorLayer,QgsField,QgsVectorFileWriter,QgsTextFormat,\
    QgsPalLayerSettings,QgsVectorLayerSimpleLabeling,QgsSimpleLineSymbolLayer,QgsSingleSymbolRenderer,QgsGeometry
from qgis.gui import QgsLayerTreeView,QgsMessageBar,QgsMapToolIdentifyFeature,QgsMapCanvas,QgsMapToolPan
import traceback

from qfluentwidgets import Flyout,setTheme,setThemeColor,Theme,MessageBox,ColorPickerButton

from widgets.draw_dialog_webSampleProjectListDialog import WebSampleProjectListDialogClass

from yoyiUtils.custom_maptool import *
from yoyiUtils.yoyiRenderProp import yoyiShpPropClass
from yoyiUtils.yoyiFile import readYamlToDict,checkTifList
from yoyiUtils.yoyiSamRequest import samWeber,postGisWeber

from appConfig import yoyiSetting

PROJECT = QgsProject.instance()

class ReviewWidgetWindowClass(QMainWindow,Ui_reviewWorkWindow):
    def __init__(self,parent=None):
        super(ReviewWidgetWindowClass, self).__init__(parent)
        self.parentWindow = parent
        self.setting = yoyiSetting()
        self.spMapCanvas = None
        self.setupUi(self)

        self.colorBtn = ColorPickerButton(QColor(255, 0, 0), '主题颜色选择', self, enableAlpha=True)
        self.horizontalLayout_Color.addWidget(self.colorBtn)
        self.rejectCBox.addItems(["勾画遗漏", "勾画太多", "勾画类型错误", "边界不贴合轮廓"])
        self.rejectCBox.setCurrentIndex(0)

        self.changeEnables(False)
        self.setObjectName("Window_Review")
        self.connectFunc()
        self.firstLoad = True

    def changeEnables(self, states):
        self.refreshWorkPb.setEnabled(states)
        self.loadWmsPb.setEnabled(states)

        self.rgbRender.setEnabled(states)
        self.bgrRender.setEnabled(states)

        self.lineRender.setEnabled(states)
        self.fillRender.setEnabled(states)
        self.fillLineRender.setEnabled(states)

        self.colorBtn.setEnabled(states)

        self.rejectPb.setEnabled(states)
        self.giveUpPb.setEnabled(states)

        self.lastPb.setEnabled(states)
        self.nextPb.setEnabled(states)

    def unsetMemberUI(self):
        self.deleteLayerChild(self.tifLayer)
        del self.drawLayer

    def initMember(self):
        # wms
        self.sw = samWeber()
        self.wmsLayer = None
        self.yspc = yoyiShpPropClass()
        # server
        self.pgw = postGisWeber()
        # 一些默认值
        self.workCfg = osp.join(self.workDir, "workDir.cfg")
        self.tifDir = osp.join(self.workDir, "img")

        contentDict = readYamlToDict(self.workCfg)
        self.projectName = contentDict['project']

        taskObjs = self.pgw.getCompletion(self.parentWindow.loginInterface.user)
        taskIndex = -1
        for i in range(len(taskObjs)):
            hardDir = taskObjs[i]['hardDir']
            if hardDir == self.projectName:
                taskIndex = i
                break

        self.uniqueId = taskObjs[taskIndex]['uniqueId']
        self.tifList = taskObjs[taskIndex]['imgName']['completion1review0']
        self.reasonDict : dict = taskObjs[taskIndex]['reason']
        self.tifLayer = QgsRasterLayer(osp.join(self.tifDir, self.tifList[0]))
        # 初始化矢量
        self.drawLayer = QgsVectorLayer("MultiPolygon", "#INTERDRAW#交互式样本勾画图层", "memory")
        self.drawLayer.setCrs(self.tifLayer.crs())
        self.drawLayer.setRenderer(self.yspc.createDiySymbol(self.getShpColor(), lineWidth='0.7', isFull=False))
        self.drawLayer.triggerRepaint()
        self.drawLayer.startEditing()

    def initUI(self,first=True):
        # 初始化影像列表 -- 地图画布 -- 颜色
        self.initListModel()
        if first:
            self.initSpMapCanvas(0)

        # project pkg label
        self.projectLabel.setText(self.projectName)

    def connectFunc(self):

        self.openProjectPb.clicked.connect(self.actionOpenProjectTriggered)
        self.refreshWorkPb.clicked.connect(self.refreshWorkPbTriggered)
        self.loadWmsPb.clicked.connect(self.loadWmsTriggered)

        self.rgbRender.clicked.connect(self.rgbRenderTriggered)
        self.bgrRender.clicked.connect(self.bgrRenderTriggered)
        self.reSizeExtent.clicked.connect(self.reSizeExtentTriggered)

        self.lastPb.clicked.connect(self.lastPbTriggered)
        self.nextPb.clicked.connect(self.nextPbTriggered)
        self.rejectPb.clicked.connect(self.rejectPbTriggered)
        self.giveUpPb.clicked.connect(self.giveUpPbTriggered)

        self.renderBtnGroup.buttonClicked.connect(self.changeRender)
        self.colorBtn.colorChanged.connect(self.changeRender)

    # 打开项目
    def actionOpenProjectTriggered(self):
        savePreDir = self.setting.configSettingReader.value('saveDir', type=str)
        isDark = self.setting.configSettingReader.value('windowStyle', type=int)
        lightBgColor = self.setting.configSettingReader.value('lightBgColor', type=tuple)
        darkBgColor = self.setting.configSettingReader.value('darkBgColor', type=tuple)
        projectSelectDialog = WebSampleProjectListDialogClass(savePreDir,isDraw=False,parent=self.parentWindow)
        if isDark == 1:
            projectSelectDialog.setStyleSheet(
                f"background: rgb({darkBgColor[0]},{darkBgColor[1]},{darkBgColor[2]})")
            self.canvasBg = darkBgColor
        else:
            projectSelectDialog.setStyleSheet(
                f"background: rgb({lightBgColor[0]},{lightBgColor[1]},{lightBgColor[2]})")
            self.canvasBg = lightBgColor
        projectSelectDialog.exec_()
        fileDir = osp.join(savePreDir,
                           projectSelectDialog.selectedProject) if projectSelectDialog.selectedProject else None
        print(fileDir)
        projectSelectDialog.deleteLater()
        if fileDir and osp.exists(fileDir) and osp.exists(osp.join(fileDir, "workDir.cfg")):
            sw = samWeber()
            tempUniqueId = sw.searchUniqueIdByProject(osp.basename(fileDir))
            if tempUniqueId is None:
                MessageBox('警告', "未找到该勾画项目！！！", self.parentWindow).exec_()
            else:
                self.workDir = fileDir
                if self.firstLoad:
                    self.initMember()
                    self.initUI()
                    self.changeEnables(True)
                    self.firstLoad = False
                else:
                    self.unsetMemberUI()
                    self.initMember()
                    self.initUI(first=False)
                    self.changeMapTif(0)
        elif fileDir and not osp.exists(fileDir):
            MessageBox('警告', "您所选文件夹不存在！！！", self.parentWindow).exec_()
            return
        elif fileDir and not osp.exists(osp.join(fileDir, "workDir.cfg")):
            MessageBox('警告', "您所选文件夹不是人工作业文件夹", self.parentWindow).exec_()
            return
        else:
            return

    def loadWmsTriggered(self):
        if self.loadWmsPb.isChecked():
            wms = r"crs=EPSG:3857&format&type=xyz&url=https://tile.charmingglobe.com/tile/china2022/tms/%7Bz%7D/%7Bx%7D/%7B-y%7D?v%3Dv1%26token%3DBearer%20bc5bb178739745ebac0643579295202a&zmax=18&zmin=0"
            self.wmsLayer = QgsRasterLayer(wms, "WMS", 'wms')
            self.addLayerSp()
        else:
            self.wmsLayer = None
            self.addLayerSp()

    def refreshWorkPbTriggered(self):
        taskObjs = self.pgw.getCompletion(self.parentWindow.loginInterface.user)
        taskIndex = -1
        for i in range(len(taskObjs)):
            hardDir = taskObjs[i]['hardDir']
            if hardDir == self.projectName:
                taskIndex = i
                break
        uniqueId = taskObjs[taskIndex]['uniqueId']
        tifList = taskObjs[taskIndex]['imgName']['completion1review0']
        if len(tifList) == 0:
            MessageBox('提示', "您已完成所有任务", self.parentWindow).exec_()
        else:
            self.unsetMemberUI()
            self.initMember()
            self.initUI(first=False)
            self.changeMapTif(0)

    def initListModel(self):
        self.slm = QStringListModel()
        self.slm.setStringList(self.tifList)
        self.listView.setModel(self.slm)
        self.listView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.listView.setEnabled(False)


    def changeMapTif(self,index):
        if self.tifLayer:
            self.deleteLayerChild(self.tifLayer)
        self.tifLayer = QgsRasterLayer(osp.join(self.tifDir,self.tifList[index]))

        # 重置驳回lineEdit
        self.reasonLineEdit.clear()

        # 显示驳回原因
        if self.tifList[index] in self.reasonDict.keys():
            self.errorReasonLabel.setText(self.reasonDict[self.tifList[index]])
        else:
            self.errorReasonLabel.setText('Null')

        # 从 postgis 中获取矢量
        self.drawLayer.deleteFeatures(self.drawLayer.allFeatureIds())
        wkts, types = self.pgw.getHardFeature(self.uniqueId, osp.basename(self.tifLayer.source()))
        for wkt, type in zip(wkts, types):
            #print(wkt)
            feat = QgsFeature(self.drawLayer.fields())
            feat.setGeometry(QgsGeometry.fromWkt(wkt))
            #feat.setAttribute("value",type)
            self.drawLayer.addFeature(feat)
        self.drawLayer.commitChanges(False)

        if index == 0:
            self.spMapCanvas.setDestinationCrs(self.tifLayer.crs())
        self.addLayerSp()
        self.listView.setCurrentIndex(self.slm.index(index,0))
        self.processLabel.setText(f"{self.listView.currentIndex().row()+1}/{len(self.tifList)}")
        if self.rgbRender.isChecked():
            self.rgbRenderTriggered()
        else:
            self.bgrRenderTriggered()

    def getShpColor(self):
        return f"{self.colorBtn.color.red()},{self.colorBtn.color.green()},{self.colorBtn.color.blue()}"


    def lastPbTriggered(self):
        if self.listView.currentIndex().row() == 0:
            MessageBox('提示', "您的任务已经是第一个了", self.parentWindow).exec_()
        else:
            self.changeMapTif(self.listView.currentIndex().row()-1)

    def nextPbTriggered(self):

        self.pgw.passed(self.uniqueId,osp.basename(self.tifLayer.source()))

        if self.listView.currentIndex().row() == len(self.tifList)-1:
            MessageBox('提示', "您的任务已经是最后一个了", self.parentWindow).exec_()
        else:
            self.changeMapTif(self.listView.currentIndex().row()+1)

    def rejectPbTriggered(self):

        self.pgw.rejected(
            self.uniqueId,osp.basename(self.tifLayer.source()),
            self.rejectCBox.currentText()+" "+self.reasonLineEdit.text()
        )

        if self.listView.currentIndex().row() == len(self.tifList)-1:
            MessageBox('提示', "您的任务已经是最后一个了", self.parentWindow).exec_()
        else:
            self.changeMapTif(self.listView.currentIndex().row()+1)

    def giveUpPbTriggered(self):
        w = MessageBox(
            '警告',
            '您确定要废弃该张切片吗？',
            self.parentWindow
        )
        w.yesButton.setText('确定废弃')
        w.cancelButton.setText('算了算了')
        if w.exec():

            self.pgw.giveuped(self.uniqueId, osp.basename(self.tifLayer.source()))

            if self.listView.currentIndex().row() == len(self.tifList)-1:
                MessageBox('提示', "您的任务已经是最后一个了", self.parentWindow).exec_()
            else:
                self.changeMapTif(self.listView.currentIndex().row()+1)

    def changeRender(self):
        if self.lineRender.isChecked():
            self.drawLayer.setRenderer(self.yspc.createDiySymbol(self.getShpColor(), lineWidth='0.7', isFull=False))
        elif self.fillRender.isChecked():
            self.drawLayer.setRenderer(self.yspc.createDiySymbol(self.getShpColor(), lineWidth='0.7', isFull=True))
        elif self.fillLineRender.isChecked():
            self.drawLayer.setRenderer(self.yspc.createDiySymbol(self.getShpColor(), lineWidth='0.3', isFull=True,fullPattern="line",distance=10))
        self.drawLayer.triggerRepaint()

    # 渲染 -- 范围调整等细节实现
    def rgbRenderTriggered(self):
        self.tifLayer.renderer().setRedBand(1)
        self.tifLayer.renderer().setGreenBand(2)
        self.tifLayer.renderer().setBlueBand(3)
        self.tifLayer.triggerRepaint()

    def bgrRenderTriggered(self):
        self.tifLayer.renderer().setRedBand(3)
        self.tifLayer.renderer().setGreenBand(2)
        self.tifLayer.renderer().setBlueBand(1)
        self.tifLayer.triggerRepaint()

    def reSizeExtentTriggered(self):
        tempExtent: QgsRectangle = self.tifLayer.extent()
        self.spMapCanvas.setExtent(tempExtent.buffered(0.0001))
        self.spMapCanvas.refresh()

    def initSpMapCanvas(self, index):
        self.spMapCanvas = QgsMapCanvas(self)
        self.spMapCanvas.setCanvasColor(QColor(self.canvasBg[0], self.canvasBg[1], self.canvasBg[2]))
        hl = QHBoxLayout(self.frame)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.addWidget(self.spMapCanvas)
        self.changeMapTif(0)
        if index > 0 and index < len(self.tifList) - 1:
            self.changeMapTif(index)

    def addLayerSp(self):
        if self.tifLayer.isValid():
            if self.wmsLayer:
                print(self.wmsLayer.isValid())
                layers = [self.drawLayer] + [self.tifLayer] + [self.wmsLayer]
            else:
                layers = [self.drawLayer] + [self.tifLayer]
            tempExtent: QgsRectangle = self.tifLayer.extent()
            self.spMapCanvas.setLayers(layers)
            self.spMapCanvas.setExtent(tempExtent.buffered(0.0001))
            self.spMapCanvas.refresh()
        else:
            print('图层无效.')

    def deleteLayerChild(self,layer):
        PROJECT.removeMapLayer(layer)
        self.spMapCanvas.refresh()
