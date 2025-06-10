import sys
from datetime import datetime

from ui.historyWindow import Ui_Form

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout,QSpacerItem,QSizePolicy

from qfluentwidgets import (CardWidget, setTheme, Theme, IconWidget, BodyLabel,SubtitleLabel, CaptionLabel, PushButton,
                            TransparentToolButton, RoundMenu, Action,SmoothScrollArea,
                            InfoBar,InfoBarPosition,ProgressRing,IndeterminateProgressRing,MessageBox,Flyout)
from qfluentwidgets import FluentIcon as FIF

from widgets.tifProcess_raster2shpDialog import Raster2ShpDialog

from yoyiUtils.yoyiThread import raster2ShpBatchRunClass,rasterCalNormBatchRunClass,rasterZonalStaticRunClass,\
    shapeFileFixGeometryRunClass

class ThreadCard(CardWidget):
    def __init__(self,icon,algoTitle,timeTitle,inputFileContent,resDirContent,parent=None):
        super().__init__(parent)
        self.parentWindow = parent
        self.overContent = None

        self.algoTitle = algoTitle
        self.timeTitle = timeTitle

        self.iconWidget = IconWidget(icon)
        self.algoTitleLabel = BodyLabel(algoTitle, self)
        self.inputContentLabel = CaptionLabel("输入路径: "+inputFileContent, self)
        self.resDirContentLabel = CaptionLabel("结果路径: "+resDirContent, self)

        self.processRing = ProgressRing(self)
        self.processRing.setTextVisible(True)

        self.titleLabel = BodyLabel("开始时间:"+timeTitle, self)

        self.openButton = PushButton('查看结果', self)
        self.delButton = PushButton('删除历史记录', self)

        self.endLabel = BodyLabel("结束状态: 未结束", self)

        self.hBoxLayout = QHBoxLayout(self)
        self.vBoxLayout = QVBoxLayout()

        #self.setFixedHeight(73)
        self.iconWidget.setFixedSize(48, 48)
        self.resDirContentLabel.setTextColor("#606060", "#d2d2d2")
        self.openButton.setFixedWidth(120)
        self.delButton.setFixedWidth(120)

        self.hBoxLayout.setContentsMargins(20, 11, 11, 11)
        self.hBoxLayout.setSpacing(20)
        self.hBoxLayout.addWidget(self.iconWidget)
        self.hBoxLayout.addWidget(self.algoTitleLabel)

        self.hBoxLayout.addWidget(self.processRing)
        self.hBoxLayout.addWidget(self.titleLabel)

        self.hBoxLayout.addWidget(self.openButton, 0, Qt.AlignLeft)
        self.hBoxLayout.addWidget(self.delButton, 0, Qt.AlignLeft)

        self.hBoxLayout.addStretch(1)

        self.hBoxLayout.addWidget(self.endLabel)

        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setSpacing(0)
        self.vBoxLayout.addWidget(self.inputContentLabel, 0, Qt.AlignVCenter)
        self.vBoxLayout.addWidget(self.resDirContentLabel, 0, Qt.AlignVCenter)
        self.vBoxLayout.setAlignment(Qt.AlignVCenter)
        self.hBoxLayout.addLayout(self.vBoxLayout)


        self.openButton.clicked.connect(self.openButtonClicked)
        self.delButton.clicked.connect(self.delButtonClicked)

    def createSuccessInfoBar(self):
        InfoBar.success(
            title=f"算法运行结束",
            content=f"{self.algoTitle}-{self.timeTitle}运行结束",
            orient=Qt.Horizontal,
            isClosable=False,
            position=InfoBarPosition.TOP,
            # position='Custom',   # NOTE: use custom info bar manager
            duration=2000,
            parent=self.parentWindow
        )

    def updateProcess(self,proc):
        self.processRing.setVal(proc)

    def finishThread(self,data):
        self.overContent = data
        self.processRing.setVal(100)
        self.endLabel.setText("结束状态: 已完成😊")
        self.createSuccessInfoBar()

    def openButtonClicked(self):
        if self.overContent:
            Flyout.create(
                icon=FIF.HISTORY,
                title='查看结果',
                content="已完成： "+self.overContent,
                target=self.openButton,
                parent=self,
                isClosable=True
            )
        else:
            Flyout.create(
                icon=FIF.HISTORY,
                title='查看结果',
                content="进程还在运行中...",
                target=self.openButton,
                parent=self,
                isClosable=True
            )

    def delButtonClicked(self):
        if self.overContent:
            self.deleteLater()
        else:
            Flyout.create(
                icon=FIF.HISTORY,
                title='删除历史记录',
                content="进程还在运行中，不允许删除",
                target=self.delButton,
                parent=self,
                isClosable=True
            )

class ThreadCardWidget(QWidget,Ui_Form):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.parentWindow = parent
        self.setObjectName("widget_thread")

    # inputFile 用来展示的，输出文件路径   fileList 实际运行的参数，是一个数组
    def addRaster2ShpThreadCard(self,inputFile,fileList,fieldName,use8Connect,postName,resDir):
        currentTime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tempThreadObjName = "raster2shpThread_" + datetime.now().strftime('%m%d%H%M%S')

        card = ThreadCard(":/img/icoNew/gis/open_tif.png", "栅格转矢量进程", currentTime, inputFile, resDir, parent=self)
        self.layoutCard.addWidget(card, alignment=Qt.AlignTop)

        setattr(self.parentWindow, tempThreadObjName,
                raster2ShpBatchRunClass(fileList,resDir,fieldName,postName,rts8Connect=use8Connect))
        exec(f"self.parentWindow.{tempThreadObjName}.signal_process.connect(card.updateProcess)")
        exec(f"self.parentWindow.{tempThreadObjName}.signal_over.connect(card.finishThread)")
        exec(f"self.parentWindow.{tempThreadObjName}.start()")

    def addRasterCalNormThreadCard(self,inputFile,fileList,algoType,algoName,postName,resDir):
        currentTime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tempThreadObjName = "rasterCalNormThread_" + datetime.now().strftime('%m%d%H%M%S')
        card = ThreadCard(":/img/icoNew/gis/open_tif.png", "栅格归一化指数计算进程", currentTime, inputFile, resDir, parent=self)
        self.layoutCard.addWidget(card, alignment=Qt.AlignTop)

        setattr(self.parentWindow, tempThreadObjName,
                rasterCalNormBatchRunClass(fileList, resDir,postName,algoType,algoName))
        exec(f"self.parentWindow.{tempThreadObjName}.signal_process.connect(card.updateProcess)")
        exec(f"self.parentWindow.{tempThreadObjName}.signal_over.connect(card.finishThread)")
        exec(f"self.parentWindow.{tempThreadObjName}.start()")

    def addRasterZonalStaticThreadCard(self,inputTif,inputShp,outShp):
        currentTime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tempThreadObjName = "rasterZonalThread_" + datetime.now().strftime('%m%d%H%M%S')
        card = ThreadCard(":/img/icoNew/gis/open_tif.png", "栅格归一化指数计算进程", currentTime, inputTif, outShp, parent=self)
        self.layoutCard.addWidget(card, alignment=Qt.AlignTop)

        setattr(self.parentWindow, tempThreadObjName,
                rasterZonalStaticRunClass(inputTif,inputShp,outShp))
        exec(f"self.parentWindow.{tempThreadObjName}.signal_process.connect(card.updateProcess)")
        exec(f"self.parentWindow.{tempThreadObjName}.signal_over.connect(card.finishThread)")
        exec(f"self.parentWindow.{tempThreadObjName}.start()")

    def addShapeFileFixGeometryThreadCard(self,inputFile,fileList,postName,resDir):
        currentTime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tempThreadObjName = "rasterFixGeoThread_" + datetime.now().strftime('%m%d%H%M%S')
        card = ThreadCard(":/img/icoNew/gis/open_shp.png", "矢量几何修复进程", currentTime, inputFile, resDir, parent=self)
        self.layoutCard.addWidget(card, alignment=Qt.AlignTop)

        setattr(self.parentWindow, tempThreadObjName,
                shapeFileFixGeometryRunClass(fileList,resDir,postName))
        exec(f"self.parentWindow.{tempThreadObjName}.signal_process.connect(card.updateProcess)")
        exec(f"self.parentWindow.{tempThreadObjName}.signal_over.connect(card.finishThread)")
        exec(f"self.parentWindow.{tempThreadObjName}.start()")
