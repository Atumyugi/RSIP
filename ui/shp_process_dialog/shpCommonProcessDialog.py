# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'shpCommonProcessDialogOWNkmU.ui'
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from qfluentwidgets import (
    ToolButton,
    BodyLabel,
    LineEdit
)
from qfluentwidgets import FluentIcon as FIF

class Ui_shpCommonProcessDialog(object):
    
    def setupUi(self, shpCommonProcessDialog):
        if not shpCommonProcessDialog.objectName():
            shpCommonProcessDialog.setObjectName(u"shpCommonProcessDialog")
        shpCommonProcessDialog.resize(500, 400)
        self.verticalLayout = QVBoxLayout(shpCommonProcessDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.inputFile_horizontalLayout = QHBoxLayout()
        self.inputFile_horizontalLayout.setObjectName(u"inputFile_horizontalLayout")
        self.inputFile_BodyLabel = BodyLabel(shpCommonProcessDialog)
        self.inputFile_BodyLabel.setObjectName(u"inputFile_BodyLabel")

        self.inputFile_horizontalLayout.addWidget(self.inputFile_BodyLabel)

        self.inputFile_LineEdit = LineEdit(shpCommonProcessDialog)
        self.inputFile_LineEdit.setObjectName(u"inputFile_LineEdit")

        self.inputFile_horizontalLayout.addWidget(self.inputFile_LineEdit)

        self.inputFile_ToolButton = ToolButton(shpCommonProcessDialog)
        self.inputFile_ToolButton.setObjectName(u"inputFile_ToolButton")
        self.inputFile_ToolButton.setIcon(FIF.MORE)
        self.inputFile_horizontalLayout.addWidget(self.inputFile_ToolButton)


        self.verticalLayout.addLayout(self.inputFile_horizontalLayout)

        self.outputFile_horizontalLayout = QHBoxLayout()
        self.outputFile_horizontalLayout.setObjectName(u"outputFile_horizontalLayout")
        self.outputFile_BodyLabel = BodyLabel(shpCommonProcessDialog)
        self.outputFile_BodyLabel.setObjectName(u"outputFile_BodyLabel")

        self.outputFile_horizontalLayout.addWidget(self.outputFile_BodyLabel)

        self.outputFile_LineEdit = LineEdit(shpCommonProcessDialog)
        self.outputFile_LineEdit.setObjectName(u"outputFile_LineEdit")

        self.outputFile_horizontalLayout.addWidget(self.outputFile_LineEdit)

        self.outputFile_ToolButton = ToolButton(shpCommonProcessDialog)
        self.outputFile_ToolButton.setObjectName(u"outputFile_ToolButton")
        self.outputFile_ToolButton.setIcon(FIF.MORE)

        self.outputFile_horizontalLayout.addWidget(self.outputFile_ToolButton)


        self.verticalLayout.addLayout(self.outputFile_horizontalLayout)

        self.tolerance_horizontalLayout = QHBoxLayout()
        self.tolerance_horizontalLayout.setObjectName(u"tolerance_horizontalLayout")
        self.tolerance_BodyLabel = BodyLabel(shpCommonProcessDialog)
        self.tolerance_BodyLabel.setObjectName(u"tolerance_BodyLabel")

        self.tolerance_horizontalLayout.addWidget(self.tolerance_BodyLabel)

        self.tolerance_LineEdit = LineEdit(shpCommonProcessDialog)
        self.tolerance_LineEdit.setObjectName(u"tolerance_LineEdit")

        self.tolerance_horizontalLayout.addWidget(self.tolerance_LineEdit)


        self.verticalLayout.addLayout(self.tolerance_horizontalLayout)

        self.minHoleArea_horizontalLayout = QHBoxLayout()
        self.minHoleArea_horizontalLayout.setObjectName(u"minHoleArea_horizontalLayout")
        self.minHoleArea_BodyLabel = BodyLabel(shpCommonProcessDialog)
        self.minHoleArea_BodyLabel.setObjectName(u"minHoleArea_BodyLabel")

        self.minHoleArea_horizontalLayout.addWidget(self.minHoleArea_BodyLabel)

        self.minHoleArea_LineEdit = LineEdit(shpCommonProcessDialog)
        self.minHoleArea_LineEdit.setObjectName(u"minHoleArea_LineEdit")

        self.minHoleArea_horizontalLayout.addWidget(self.minHoleArea_LineEdit)


        self.verticalLayout.addLayout(self.minHoleArea_horizontalLayout)

        self.removeArea_horizontalLayout = QHBoxLayout()
        self.removeArea_horizontalLayout.setObjectName(u"removeArea_horizontalLayout")
        self.removeArea_BodyLabel = BodyLabel(shpCommonProcessDialog)
        self.removeArea_BodyLabel.setObjectName(u"removeArea_BodyLabel")

        self.removeArea_horizontalLayout.addWidget(self.removeArea_BodyLabel)

        self.removeArea_LineEdit = LineEdit(shpCommonProcessDialog)
        self.removeArea_LineEdit.setObjectName(u"removeArea_LineEdit")

        self.removeArea_horizontalLayout.addWidget(self.removeArea_LineEdit)


        self.verticalLayout.addLayout(self.removeArea_horizontalLayout)

        self.buttonBox = QDialogButtonBox(shpCommonProcessDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.verticalLayout.addWidget(self.buttonBox)


        self.retranslateUi(shpCommonProcessDialog)

        QMetaObject.connectSlotsByName(shpCommonProcessDialog)
    # setupUi

    def retranslateUi(self, shpCommonProcessDialog):
        shpCommonProcessDialog.setWindowTitle(QCoreApplication.translate("shpCommonProcessDialog", u"Vector Post-Processing", None))
        self.inputFile_BodyLabel.setText(QCoreApplication.translate("shpCommonProcessDialog", u"Input File", None))
        self.outputFile_BodyLabel.setText(QCoreApplication.translate("shpCommonProcessDialog", u"Output File", None))
        self.tolerance_BodyLabel.setText(QCoreApplication.translate("shpCommonProcessDialog", u"Simplify Tolerance", None))
        self.minHoleArea_BodyLabel.setText(QCoreApplication.translate("shpCommonProcessDialog", u"Minimum Hole Area", None))
        self.removeArea_BodyLabel.setText(QCoreApplication.translate("shpCommonProcessDialog", u"Minimum Polygon Area", None))
    # retranslateUi

