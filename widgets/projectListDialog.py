import os
import os.path as osp

from ui.projectListDialog import Ui_Dialog


from PyQt5.QtCore import Qt,QStringListModel,QPoint,QSize
from PyQt5.QtWidgets import QFrame, QWidget,QMainWindow,QAbstractItemView,QApplication, QDialog, QHBoxLayout, QVBoxLayout,QSpacerItem,QFileDialog,QSizePolicy
from PyQt5.QtGui import QIcon,QCursor,QFont,QPixmap

from qfluentwidgets import PixmapLabel,PrimaryPushButton,CardWidget,SubtitleLabel,StrongBodyLabel,BodyLabel
from qfluentwidgets import FluentIcon as FIF

from yoyiUtils.yoyiFile import checkChildDirI,deleteDir,getInfoByLocalDrawProject


import yoyirs_rc

class LocalProjectListDialogClass(Ui_Dialog,QDialog):
    def __init__(self,projectPath,parent=None):
        super().__init__(parent=parent)
        self.parentWindow = parent
        self.projectPath = projectPath
        self.selectedProject = None
        self.setupUi(self)
        self.setObjectName("Dialog_ProjectList_Local")
        self.initMember()
        self.initUI()
    
    def initMember(self):
        self.selectedProject = None
        self.delete = None

    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        self.childProjects = checkChildDirI(self.projectPath)
        for childProject in self.childProjects:
            projectPath = osp.join(self.projectPath,childProject)
            self.createCardWidget(projectPath)
        spacerItem = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.verticalLayout_2.addItem(spacerItem)
    def openPbClicked(self,projectName):
        self.selectedProject = projectName
        self.delete = False
        self.close()
    
    def deletePbClicked(self,projectName):
        self.selectedProject = projectName
        self.delete = True
        self.close()

    def createCardWidget(self,projectPath):
        projectName = osp.basename(projectPath)
        getRes = getInfoByLocalDrawProject(projectPath)
        if getRes:
            modificationStr,tifPath,codemapStr,snapPath = getRes
            openEnable = True
        else:
            modificationStr = "项目已损坏"
            tifPath = "项目已损坏"
            codemapStr = "项目已损坏"
            snapPath = None
            openEnable = False
        cardWidget = CardWidget(self)
        cardWidget.setObjectName(f"card_{projectName}")
        cardLayout = QHBoxLayout(cardWidget)
        cardLayout.setObjectName(f"cardLayout_{projectName}")

        pixelmapLabel = PixmapLabel(cardWidget)
        pixelmapSizePolicy = QSizePolicy(QSizePolicy.Preferred,QSizePolicy.Preferred)
        pixelmapSizePolicy.setHorizontalStretch(0)
        pixelmapSizePolicy.setVerticalStretch(0)
        pixelmapSizePolicy.setHeightForWidth(pixelmapLabel.sizePolicy().hasHeightForWidth())
        pixelmapLabel.setSizePolicy(pixelmapSizePolicy)
        pixelmapLabel.setMinimumSize(QSize(350, 250))
        pixelmapLabel.setMaximumSize(QSize(350, 250))
        if snapPath and osp.exists(snapPath):
            pixelmapLabel.setPixmap(QPixmap(snapPath).scaled(350, 250))
        else:
            pixelmapLabel.setPixmap(QPixmap(":/img/resources/saveAsImg.png").scaled(350, 250))
        pixelmapLabel.setScaledContents(True)
        pixelmapLabel.setObjectName(f"PixmapLabel_{projectName}")
        cardLayout.addWidget(pixelmapLabel)

        rightLayout = QVBoxLayout()
        rightLayout.setObjectName(f"rightLayout_{projectName}")

        projectNameLabel = SubtitleLabel(cardWidget)
        projectNameSizePolicy = QSizePolicy(QSizePolicy.Preferred,QSizePolicy.Fixed)
        projectNameSizePolicy.setHorizontalStretch(0)
        projectNameSizePolicy.setVerticalStretch(0)
        projectNameSizePolicy.setHeightForWidth(projectNameLabel.sizePolicy().hasHeightForWidth())
        projectNameLabel.setSizePolicy(projectNameSizePolicy)
        projectNameLabel.setWordWrap(True)
        projectNameLabel.setObjectName(f"projectNameLabel_{projectName}")
        projectNameLabel.setText(f"项目名称:{projectName}")
        rightLayout.addWidget(projectNameLabel)

        lasteTimeLabel = StrongBodyLabel(cardWidget)
        lastTimeSizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        lastTimeSizePolicy.setHorizontalStretch(0)
        lastTimeSizePolicy.setVerticalStretch(0)
        lastTimeSizePolicy.setHeightForWidth(lasteTimeLabel.sizePolicy().hasHeightForWidth())
        lasteTimeLabel.setSizePolicy(lastTimeSizePolicy)
        lasteTimeLabel.setWordWrap(False)
        lasteTimeLabel.setObjectName(f"lasteTimeLabel_{projectName}")
        lasteTimeLabel.setText(f"最后修改: {modificationStr}")
        rightLayout.addWidget(lasteTimeLabel)

        tifPathTitle = StrongBodyLabel(cardWidget)
        tifPathTitleSizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        tifPathTitleSizePolicy.setHorizontalStretch(0)
        tifPathTitleSizePolicy.setVerticalStretch(0)
        tifPathTitleSizePolicy.setHeightForWidth(tifPathTitle.sizePolicy().hasHeightForWidth())
        tifPathTitle.setSizePolicy(tifPathTitleSizePolicy)
        tifPathTitle.setWordWrap(False)
        tifPathTitle.setObjectName(f"tifPathTitle_{projectName}")
        tifPathTitle.setText("影像路径：")
        rightLayout.addWidget(tifPathTitle)

        tifPathLabel = BodyLabel(cardWidget)
        tifPathLabelSizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        tifPathLabelSizePolicy.setHorizontalStretch(0)
        tifPathLabelSizePolicy.setVerticalStretch(0)
        tifPathLabelSizePolicy.setHeightForWidth(tifPathLabel.sizePolicy().hasHeightForWidth())
        tifPathLabel.setSizePolicy(tifPathLabelSizePolicy)
        tifPathLabel.setWordWrap(True)
        tifPathLabel.setObjectName(f"tifPathLabel_{projectName}")
        tifPathLabel.setText(tifPath)
        rightLayout.addWidget(tifPathLabel)

        drawTypeTitle = StrongBodyLabel(cardWidget)
        drawTypeTitleSizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        drawTypeTitleSizePolicy.setHorizontalStretch(0)
        drawTypeTitleSizePolicy.setVerticalStretch(0)
        drawTypeTitleSizePolicy.setHeightForWidth(drawTypeTitle.sizePolicy().hasHeightForWidth())
        drawTypeTitle.setSizePolicy(drawTypeTitleSizePolicy)
        drawTypeTitle.setWordWrap(False)
        drawTypeTitle.setObjectName(f"drawTypeTitle_{projectName}")
        drawTypeTitle.setText("勾画类型：")
        rightLayout.addWidget(drawTypeTitle)

        drawTypeLabel = BodyLabel(cardWidget)
        drawTypeLabelSizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        drawTypeLabelSizePolicy.setHorizontalStretch(0)
        drawTypeLabelSizePolicy.setVerticalStretch(0)
        drawTypeLabelSizePolicy.setHeightForWidth(drawTypeLabel.sizePolicy().hasHeightForWidth())
        drawTypeLabel.setSizePolicy(drawTypeLabelSizePolicy)
        drawTypeLabel.setWordWrap(True)
        drawTypeLabel.setObjectName(f"drawTypeLabel_{projectName}")
        drawTypeLabel.setText(codemapStr)
        rightLayout.addWidget(drawTypeLabel)

        openPb = PrimaryPushButton(cardWidget)
        openPb.setObjectName(f"openPb_{projectName}")
        openPb.setIcon(FIF.FOLDER_ADD)
        openPb.setText("打开项目")
        openPb.setEnabled(openEnable)
        openPb.clicked.connect(lambda: self.openPbClicked(projectName))
        rightLayout.addWidget(openPb)

        deletePb = PrimaryPushButton(cardWidget)
        deletePb.setObjectName(f"deletePb_{projectName}")
        deletePb.setIcon(FIF.DELETE)
        deletePb.setText("删除项目")
        deletePb.clicked.connect(lambda: self.deletePbClicked(projectName))
        rightLayout.addWidget(deletePb)

        cardLayout.addLayout(rightLayout)

        self.verticalLayout_2.addWidget(cardWidget)