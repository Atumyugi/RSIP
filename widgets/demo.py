import sys

import os
import os.path as osp
from ui.projectListDialog import Ui_Dialog

from PyQt5.QtCore import Qt,QModelIndex,QSize
from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QVBoxLayout,QSpacerItem,QFileDialog,QSizePolicy
from PyQt5.QtGui import QFont,QCursor,QPixmap
from qfluentwidgets import PixmapLabel,PrimaryPushButton,CardWidget,SubtitleLabel,StrongBodyLabel,BodyLabel
from qfluentwidgets import FluentIcon as FIF
class demoDialog(Ui_Dialog,QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.parentWindow = parent
        self.setupUi(self)
        self.initUI()
    
    def openPbClicked(self,index):
        print(index,"被点击")

    def createCardWidget(self,index):

        pngPath = r"C:\Users\lzq\Pictures\210\3asdasd.png"

        cardWidget = CardWidget(self)
        cardWidget.setObjectName(f"card_{index}")
        cardLayout = QHBoxLayout(cardWidget)
        cardLayout.setObjectName(f"cardLayout_{index}")

        pixelmapLabel = PixmapLabel(cardWidget)
        pixelmapSizePolicy = QSizePolicy(QSizePolicy.Preferred,QSizePolicy.Preferred)
        pixelmapSizePolicy.setHorizontalStretch(0)
        pixelmapSizePolicy.setVerticalStretch(0)
        pixelmapSizePolicy.setHeightForWidth(pixelmapLabel.sizePolicy().hasHeightForWidth())
        pixelmapLabel.setSizePolicy(pixelmapSizePolicy)
        pixelmapLabel.setMinimumSize(QSize(350, 250))
        pixelmapLabel.setMaximumSize(QSize(350, 250))
        if osp.exists(pngPath):
            pixelmapLabel.setPixmap(QPixmap(pngPath).scaled(350, 250))
        else:
            pixelmapLabel.setPixmap(QPixmap(FIF.CLOSE.path()).scaled(350, 250))
        pixelmapLabel.setScaledContents(True)
        pixelmapLabel.setObjectName(f"PixmapLabel_{index}")
        cardLayout.addWidget(pixelmapLabel)

        rightLayout = QVBoxLayout()
        rightLayout.setObjectName(f"rightLayout_{index}")

        projectNameLabel = SubtitleLabel(cardWidget)
        projectNameSizePolicy = QSizePolicy(QSizePolicy.Preferred,QSizePolicy.Fixed)
        projectNameSizePolicy.setHorizontalStretch(0)
        projectNameSizePolicy.setVerticalStretch(0)
        projectNameSizePolicy.setHeightForWidth(projectNameLabel.sizePolicy().hasHeightForWidth())
        projectNameLabel.setSizePolicy(projectNameSizePolicy)
        projectNameLabel.setWordWrap(True)
        projectNameLabel.setObjectName(f"projectNameLabel_{index}")
        projectNameLabel.setText("项目名称")
        rightLayout.addWidget(projectNameLabel)

        lasteTimeLabel = StrongBodyLabel(cardWidget)
        lastTimeSizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        lastTimeSizePolicy.setHorizontalStretch(0)
        lastTimeSizePolicy.setVerticalStretch(0)
        lastTimeSizePolicy.setHeightForWidth(lasteTimeLabel.sizePolicy().hasHeightForWidth())
        lasteTimeLabel.setSizePolicy(lastTimeSizePolicy)
        lasteTimeLabel.setWordWrap(False)
        lasteTimeLabel.setObjectName(f"lasteTimeLabel_{index}")
        lasteTimeLabel.setText("最后修改: 1949/10/01 20:00:01")
        rightLayout.addWidget(lasteTimeLabel)

        tifPathTitle = StrongBodyLabel(cardWidget)
        tifPathTitleSizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        tifPathTitleSizePolicy.setHorizontalStretch(0)
        tifPathTitleSizePolicy.setVerticalStretch(0)
        tifPathTitleSizePolicy.setHeightForWidth(tifPathTitle.sizePolicy().hasHeightForWidth())
        tifPathTitle.setSizePolicy(tifPathTitleSizePolicy)
        tifPathTitle.setWordWrap(False)
        tifPathTitle.setObjectName(f"tifPathTitle_{index}")
        tifPathTitle.setText("影像路径：")
        rightLayout.addWidget(tifPathTitle)

        tifPathLabel = BodyLabel(cardWidget)
        tifPathLabelSizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        tifPathLabelSizePolicy.setHorizontalStretch(0)
        tifPathLabelSizePolicy.setVerticalStretch(0)
        tifPathLabelSizePolicy.setHeightForWidth(tifPathLabel.sizePolicy().hasHeightForWidth())
        tifPathLabel.setSizePolicy(tifPathLabelSizePolicy)
        tifPathLabel.setWordWrap(True)
        tifPathLabel.setObjectName(f"tifPathLabel_{index}")
        tifPathLabel.setText("https://map.charmingglobe.com/tile/china1m/{z}/{x}/{-y}?v=v1&token=Bearera84a40c81f784490a4c5689187054abc,https://map.charmingglobe.com/tile/china1m/{z}/{x}/{-y}?v=v1&token=Bearea84a40c81f784490a4c5689187054abc")
        rightLayout.addWidget(tifPathLabel)

        drawTypeTitle = StrongBodyLabel(cardWidget)
        drawTypeTitleSizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        drawTypeTitleSizePolicy.setHorizontalStretch(0)
        drawTypeTitleSizePolicy.setVerticalStretch(0)
        drawTypeTitleSizePolicy.setHeightForWidth(drawTypeTitle.sizePolicy().hasHeightForWidth())
        drawTypeTitle.setSizePolicy(drawTypeTitleSizePolicy)
        drawTypeTitle.setWordWrap(False)
        drawTypeTitle.setObjectName(f"drawTypeTitle_{index}")
        drawTypeTitle.setText("勾画类型：")
        rightLayout.addWidget(drawTypeTitle)

        drawTypeLabel = BodyLabel(cardWidget)
        drawTypeLabelSizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        drawTypeLabelSizePolicy.setHorizontalStretch(0)
        drawTypeLabelSizePolicy.setVerticalStretch(0)
        drawTypeLabelSizePolicy.setHeightForWidth(drawTypeLabel.sizePolicy().hasHeightForWidth())
        drawTypeLabel.setSizePolicy(drawTypeLabelSizePolicy)
        drawTypeLabel.setWordWrap(True)
        drawTypeLabel.setObjectName(f"drawTypeLabel_{index}")
        drawTypeLabel.setText("耕地，水体，建筑用地")
        rightLayout.addWidget(drawTypeLabel)

        openPb = PrimaryPushButton(cardWidget)
        openPb.setObjectName(f"openPb_{index}")
        openPb.setIcon(FIF.FOLDER_ADD)
        openPb.setText("打开项目")
        openPb.clicked.connect(lambda: self.openPbClicked(index))
        rightLayout.addWidget(openPb)

        deletePb = PrimaryPushButton(cardWidget)
        deletePb.setObjectName(f"deletePb_{index}")
        deletePb.setIcon(FIF.DELETE)
        deletePb.setText("删除项目")
        rightLayout.addWidget(deletePb)

        cardLayout.addLayout(rightLayout)

        self.verticalLayout_2.addWidget(cardWidget)
        

    def initUI(self):
        self.createCardWidget(1)
        self.createCardWidget(2)
        self.createCardWidget(3)
        self.createCardWidget(4)
        spacerItem = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.verticalLayout_2.addItem(spacerItem)
        


if __name__ == '__main__':
    # enable dpi scale
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    w = demoDialog()
    w.show()
    sys.exit(app.exec_())