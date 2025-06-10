import os
import os.path as osp
from datetime import datetime
import json

from ui.infer_dialog.trainDialog import Ui_trainDialog

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
import matplotlib.ticker as ticker
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置字体为SimHei
plt.rcParams['axes.unicode_minus'] = False  # 设置正确显示负号

from PyQt5.QtCore import Qt,QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog,QFileDialog,QButtonGroup
from qfluentwidgets import MessageBox
from qfluentwidgets import FluentIcon as FIF

from yoyiUtils.qtTriggeredCommon import qtTriggeredCommonDialog
from yoyiUtils.yoyiFile import checkTifList,checkAllFileList,checkPostFileList
from yoyiUtils.yoyiTranslate import yoyiTrans
from yoyiUtils.yoyiValid import isValidDirName
from yoyiUtils.yoyiThreadTrain import SegmentTrainRunClass
import torch
import yoyirs_rc
import appConfig

class TrainDialogClass(Ui_trainDialog,QDialog):
    def __init__(self,yoyiTrs:yoyiTrans,parent=None):
        super().__init__(parent)
        self.parentWindow = parent
        self.yoyiTrs = yoyiTrs
        self.setupUi(self)
        self.initUI()
        self.connectFunc()
    
    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        self.setWindowIcon(QIcon(':/img/resources/infer/train.png'))

        # tab
        self.tabWidget.tabBar().hide()
        self.pageGroup = QButtonGroup(self)
        self.pageGroup.addButton(self.homePagePb)
        self.pageGroup.addButton(self.lossCurvePb)
        self.pageGroup.addButton(self.learningRateCurvePb)
        self.pageGroup.addButton(self.accCurvePb)
        self.pageGroup.addButton(self.miouCurvePb)
        self.tabWidget.setCurrentIndex(0)
        self.homePagePb.setChecked(True)

        # icon
        self.selectTrainsetDirPb.setIcon(FIF.MORE)
        self.selectValidsetPb.setIcon(FIF.MORE)
        self.selectTestsetPb.setIcon(FIF.MORE)
        self.selectSaveDirPB.setIcon(FIF.MORE)

        # le read only
        self.selectTrainsetDirLe.setReadOnly(True)
        self.selectValidsetDirLe.setReadOnly(True)
        self.selectTestsetDirLe.setReadOnly(True)
        self.resLE.setReadOnly(True)
        
        self.imgPostLineEdit.setReadOnly(False)
        self.labelPostLineEdit.setReadOnly(False)
        self.imgDirNameLineEdit.setReadOnly(False)
        self.labelDirNameLineEdit.setReadOnly(False)

        # gpu
        # for deviceId in range(torch.cuda.device_count()):
        #     self.selectGPUCb.addItem(torch.cuda.get_device_name(deviceId) + f"_{deviceId}",userData=deviceId)

        # init ui
        self.modelCb.addItem("SwinTransform")
        self.imgPostLineEdit.setText("png")
        self.labelPostLineEdit.setText("png")
        self.imgDirNameLineEdit.setText("image")
        self.labelDirNameLineEdit.setText("label")
        self.workDir = None
        self.ProgressRing.stop()

        # Curves
        # loss 曲线
        self.lossFig,self.lossAx = plt.subplots()
        self.lossCanvas = FigureCanvasQTAgg(self.lossFig)
        self.lossLayout.addWidget(self.lossCanvas,0,0)

        # lr 曲线
        self.lrFig,self.lrAx = plt.subplots()
        self.lrCanvas = FigureCanvasQTAgg(self.lrFig)
        self.learningRateLayout.addWidget(self.lrCanvas,0,0)

        # acc 曲线
        self.accFig,self.accAx = plt.subplots()
        self.accCanvas = FigureCanvasQTAgg(self.accFig)
        self.accLayout.addWidget(self.accCanvas,0,0)

        # miou 曲线
        self.miouFig,self.miouAx = plt.subplots()
        self.miouCanvas = FigureCanvasQTAgg(self.miouFig)
        self.miouLayout.addWidget(self.miouCanvas,0,0)

        # 存储的某些变量
        self.isTraining = False

    
    def closeEvent(self, e):
        if not self.isTraining:
            e.accept()
        else:
            reply = MessageBox(
                self.yoyiTrs._translate("退出"),
                self.yoyiTrs._translate("确定要退出吗？"),
                self
            )
            reply.yesButton.setText(self.yoyiTrs._translate("退出"))
            reply.cancelButton.setText(self.yoyiTrs._translate("取消"))
            if reply.exec():
                e.accept()
            else:
                e.ignore()
    
    def connectFunc(self):
        self.pageGroup.buttonClicked.connect(self.pageGroupClicked)
        self.selectTrainsetDirPb.clicked.connect(lambda : qtTriggeredCommonDialog().addFileDirTriggered(self.selectTrainsetDirLe,parent=self))
        self.selectValidsetPb.clicked.connect(lambda : qtTriggeredCommonDialog().addFileDirTriggered(self.selectValidsetDirLe,parent=self))
        self.selectTestsetPb.clicked.connect(lambda : qtTriggeredCommonDialog().addFileDirTriggered(self.selectTestsetDirLe,parent=self))
        self.selectSaveDirPB.clicked.connect(self.selectSaveDirPBClicked)

        self.startPb.clicked.connect(self.startPbClicked)
        
        self.refreshTrainingLogPb.clicked.connect(self.refreshTrainingLogPbClicked)

    def pageGroupClicked(self):
        if self.homePagePb.isChecked():
            self.tabWidget.setCurrentIndex(0)
        elif self.lossCurvePb.isChecked():
            self.tabWidget.setCurrentIndex(1)
        elif self.learningRateCurvePb.isChecked():
            self.tabWidget.setCurrentIndex(2)
        elif self.accCurvePb.isChecked():
            self.tabWidget.setCurrentIndex(3)
        elif self.miouCurvePb.isChecked():
            self.tabWidget.setCurrentIndex(4)
    
    def selectSaveDirPBClicked(self):
        fileDir = QFileDialog.getExistingDirectory(self, self.yoyiTrs._translate("选择文件夹"), "")
        if fileDir:
            if os.listdir(fileDir):
                MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('文件夹不为空'), self).exec_()
                return
            else:
                self.resLE.setText(fileDir)
    
    def checkLatestJson(self,dirPath):
        latestFile = None
        latestTime = -1
        for root, dirs, files in os.walk(dirPath):
            for file in files:
                if file == "scalars.json":
                    filePath = os.path.join(root, file)
                    fileModTime = os.path.getmtime(filePath)
                    print(fileModTime)
                    if fileModTime > latestTime:
                        latestTime = fileModTime
                        latestFile = filePath
        return latestFile

    def refreshTrainingLogPbClicked(self):
        try:
            latestFile = self.checkLatestJson(self.workDir)
            if latestFile:

                self.iterList = []
                self.valIterList = []
                self.lossList = []
                self.lrList = []
                self.accList = []
                self.miouList = []

                scalar = open(latestFile)
                for line in scalar:
                    info : dict = json.loads(line)
                    if 'mIoU' in info.keys():
                        self.miouList.append(info['mIoU'])
                        self.valIterList.append(info['step'])
                    else:
                        self.iterList.append(info['iter'])
                        self.lossList.append(info['loss'])
                        self.lrList.append(info['lr'])
                        self.accList.append(info['decode.acc_seg'])

                self.currentItersLE.setText(f"{self.iterList[-1]}")
                # 如果数量太多，则抽稀
                if len(self.iterList) > 40:
                    factor = round(len(self.iterList) / 40) if round(len(self.iterList) / 40)>1 else 2
                    self.iterList = self.iterList[::factor]
                    self.lossList = self.lossList[::factor]
                    self.lrList = self.lrList[::factor]
                    self.accList = self.accList[::factor]
                if len(self.valIterList) > 10:
                    factor = round(len(self.valIterList) / 10) if round(len(self.valIterList) / 10)>1 else 2
                    self.valIterList = self.valIterList[::factor]
                    self.miouList = self.miouList[::factor]

                if len(self.iterList) > 10:
                    xticksFactor = round(len(self.iterList) / 10) if round(len(self.iterList) / 10)>1 else 2
                    xticks = self.iterList[::xticksFactor]
                else:
                    xticks = self.iterList
                    
                # loss curve
                self.lossAx.cla()
                self.lossAx.set_title("Loss Curve")
                self.lossAx.xaxis.set_minor_locator(ticker.MaxNLocator(nbins=10))
                self.lossAx.plot(self.iterList,self.lossList,marker='o')
                if len(self.iterList) < 10:
                    for iter,loss in zip(self.iterList,self.lossList):
                        self.lossAx.text(iter,loss,f"{loss:.4f}")
                else:
                    self.lossAx.text(self.iterList[0],self.lossList[0],f"{self.lossList[0]:.4f}")
                    self.lossAx.text(self.iterList[-1],self.lossList[-1],f"{self.lossList[-1]:.4f}")
                self.lossAx.set_xticks(xticks)
                #self.lossAx.set_xticklabels(self.iterList)
                self.lossCanvas.draw()

                # lr curve
                self.lrAx.cla()
                self.lrAx.set_title("Learning Rate Curve")
                self.lrAx.xaxis.set_minor_locator(ticker.MaxNLocator(nbins=10))
                self.lrAx.plot(self.iterList,self.lrList,marker='o')
                if len(self.iterList) < 10:
                    for iter,lr in zip(self.iterList,self.lrList):
                        self.lrAx.text(iter,lr,f"{lr:.4e}")
                else:
                    self.lrAx.text(self.iterList[0],self.lrList[0],f"{self.lrList[0]:.4e}")
                    self.lrAx.text(self.iterList[-1],self.lrList[-1],f"{self.lrList[-1]:.4e}")
                self.lrAx.set_xticks(xticks)
                #self.lrAx.set_xticklabels(self.iterList)
                self.lrCanvas.draw()

                # acc curve
                self.accAx.cla()
                self.accAx.set_title("Accuracy Curve")
                self.accAx.xaxis.set_minor_locator(ticker.MaxNLocator(nbins=10))
                self.accAx.plot(self.iterList,self.accList,marker='o')
                if len(self.iterList) < 10:
                    for iter,acc in zip(self.iterList,self.accList):
                        self.accAx.text(iter,acc,f"{acc:.4f}")
                else:
                    self.accAx.text(self.iterList[0],self.accList[0],f"{self.accList[0]:.4f}")
                    self.accAx.text(self.iterList[-1],self.accList[-1],f"{self.accList[-1]:.4f}")
                self.accAx.set_xticks(xticks)
                #self.accAx.set_xticklabels(self.iterList)
                self.accCanvas.draw()

                # miou curve
                self.miouAx.cla()
                self.miouAx.set_title("MIoU Curve")
                self.miouAx.xaxis.set_minor_locator(ticker.MaxNLocator(nbins=10))
                self.miouAx.plot(self.valIterList,self.miouList,marker='o')
                if len(self.valIterList) < 10:
                    for iter,miou in zip(self.valIterList,self.miouList):
                        self.miouAx.text(iter,miou,f"{miou:.4f}")
                else:
                    self.miouAx.text(self.valIterList[0],self.miouList[0],f"{self.miouList[0]:.4f}")
                    self.miouAx.text(self.valIterList[-1],self.miouList[-1],f"{self.miouList[-1]:.4f}")
                self.miouAx.set_xticks(self.valIterList)
                #self.miouAx.set_xticklabels(self.valIterList)
                self.miouCanvas.draw()

        except Exception as e:
            print(e)
    
    def startPbClicked(self):
        
        # 一些状态判断
        if self.selectTrainsetDirLe.text() == "":
            MessageBox(self.yoyiTrs._translate('警告'), f'{self.trainsetDirLabel.text()} {self.yoyiTrs._translate("地址非法")}', self).exec_()
            return
        if self.selectValidsetDirLe.text() == "":
            MessageBox(self.yoyiTrs._translate('警告'), f'{self.validsetDirLabel.text()} {self.yoyiTrs._translate("地址非法")}', self).exec_()
            return
        if self.selectTestsetDirLe.text() == "":
            MessageBox(self.yoyiTrs._translate('警告'), f'{self.testsetDirLabel.text()} {self.yoyiTrs._translate("地址非法")}', self).exec_()
            return
        if self.resLE.text() == "":
            MessageBox(self.yoyiTrs._translate('警告'), f'{self.BodyLabel_26.text()} {self.yoyiTrs._translate("地址非法")}', self).exec_()
            return
        # if self.selectGPUCb.count() == 0:
        #     MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate("没有可用GPU"), self).exec_()
        #     return

        config = osp.join(appConfig.MODEL_PATH,"SwinTransformer.py")
        preModel = osp.join(appConfig.MODEL_PATH,"swin_pre.pth")
        trainDataRoot = self.selectTrainsetDirLe.text()
        valDataRoot = self.selectValidsetDirLe.text()
        testDataRoot = self.selectTestsetDirLe.text()
        workDir = self.resLE.text()
        numClasses = 2
        batchSize = self.batchSizeSpinBox.value()
        imgSize = self.imageSizeSpinBox.value()
        imgPost = self.imgPostLineEdit.text()
        labelPost = self.labelPostLineEdit.text()
        imgDirName = self.imgDirNameLineEdit.text()
        labelDirName = self.labelDirNameLineEdit.text()
        lr = self.learningRateSpinBox.value()
        iters = self.itersSpinBox.value()
        valIters = self.validItersSpinBox.value()
        #iters = 100
        #valIters = 50

        # 一些状态变更
        self.isTraining = True
        self.workDir = workDir
        self.startPb.hide()
        self.totalItersLE.setText(f"{iters}")
        self.currentItersLE.setText('0')
        self.startTimeLE.setText(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.resultDirRightLE.setText(workDir)
        self.ProgressRing.start()

        # thread 运行
        self.trainThread = SegmentTrainRunClass(config=config,
                                                preModel=preModel,
                                                trainDataRoot=trainDataRoot,
                                                valDataRoot=valDataRoot,
                                                testDataRoot=testDataRoot,
                                                workDir=workDir,
                                                numClasses=numClasses,
                                                batchSize=batchSize,
                                                imgSize=imgSize,
                                                imgPost=imgPost,
                                                labelPost=labelPost,
                                                imgDirName=imgDirName,
                                                labelDirName=labelDirName,
                                                lr = lr,
                                                iters = iters,
                                                valIters= valIters,)
        self.trainThread.signal_over.connect(self.trainThreadFinished)
        self.trainThread.start()

        self.timer = QTimer(self)
        self.timer.setInterval(1000*30)
        self.timer.timeout.connect(self.refreshTrainingLogPbClicked)
        self.timer.start()
    
    def trainThreadFinished(self,path):
        if not osp.exists(path):
            MessageBox(self.yoyiTrs._translate('警告'), f'{path}', self).exec_()
        else:
            MessageBox(self.yoyiTrs._translate('运行结束'), f'{self.yoyiTrs._translate("结果路径")}：{path}', self).exec_()
        
        del self.trainThread
        torch.cuda.empty_cache()
        self.ProgressRing.stop()
        self.isTraining = False
        self.timer.stop()

