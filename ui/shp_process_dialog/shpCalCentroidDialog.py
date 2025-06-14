# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'f:\rsdm\ui\shp_process_dialog\shpCalCentroidDialog.ui'
#
# Created by: PyQt5 UI code generator 5.15.9
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_shpCalCentroidDialog(object):
    def setupUi(self, shpCalCentroidDialog):
        shpCalCentroidDialog.setObjectName("shpCalCentroidDialog")
        shpCalCentroidDialog.resize(495, 211)
        self.verticalLayout = QtWidgets.QVBoxLayout(shpCalCentroidDialog)
        self.verticalLayout.setContentsMargins(-1, 6, -1, 7)
        self.verticalLayout.setSpacing(6)
        self.verticalLayout.setObjectName("verticalLayout")
        self.CardWidget_4 = CardWidget(shpCalCentroidDialog)
        self.CardWidget_4.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.CardWidget_4.setObjectName("CardWidget_4")
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout(self.CardWidget_4)
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.BodyLabel = BodyLabel(self.CardWidget_4)
        self.BodyLabel.setObjectName("BodyLabel")
        self.horizontalLayout_5.addWidget(self.BodyLabel)
        self.selectShpCb = ComboBox(self.CardWidget_4)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.selectShpCb.sizePolicy().hasHeightForWidth())
        self.selectShpCb.setSizePolicy(sizePolicy)
        self.selectShpCb.setObjectName("selectShpCb")
        self.horizontalLayout_5.addWidget(self.selectShpCb)
        self.verticalLayout.addWidget(self.CardWidget_4)
        self.allPartCheckBox = CheckBox(shpCalCentroidDialog)
        self.allPartCheckBox.setObjectName("allPartCheckBox")
        self.verticalLayout.addWidget(self.allPartCheckBox)
        self.CardWidget = CardWidget(shpCalCentroidDialog)
        self.CardWidget.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.CardWidget.setObjectName("CardWidget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.CardWidget)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.BodyLabel_4 = BodyLabel(self.CardWidget)
        self.BodyLabel_4.setObjectName("BodyLabel_4")
        self.horizontalLayout.addWidget(self.BodyLabel_4)
        self.resLE = LineEdit(self.CardWidget)
        self.resLE.setReadOnly(True)
        self.resLE.setObjectName("resLE")
        self.horizontalLayout.addWidget(self.resLE)
        self.selectSaveFilePB = ToolButton(self.CardWidget)
        self.selectSaveFilePB.setObjectName("selectSaveFilePB")
        self.horizontalLayout.addWidget(self.selectSaveFilePB)
        self.verticalLayout.addWidget(self.CardWidget)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem)
        self.runPB = PushButton(shpCalCentroidDialog)
        self.runPB.setObjectName("runPB")
        self.horizontalLayout_3.addWidget(self.runPB)
        self.cancelPB = PushButton(shpCalCentroidDialog)
        self.cancelPB.setObjectName("cancelPB")
        self.horizontalLayout_3.addWidget(self.cancelPB)
        self.verticalLayout.addLayout(self.horizontalLayout_3)

        self.retranslateUi(shpCalCentroidDialog)
        QtCore.QMetaObject.connectSlotsByName(shpCalCentroidDialog)

    def retranslateUi(self, shpCalCentroidDialog):
        _translate = QtCore.QCoreApplication.translate
        shpCalCentroidDialog.setWindowTitle(_translate("shpCalCentroidDialog", "Vector Cal Centroid Parameter Settings"))
        self.BodyLabel.setText(_translate("shpCalCentroidDialog", "Select Vector"))
        self.allPartCheckBox.setText(_translate("shpCalCentroidDialog", "Sub-components also create centroids"))
        self.BodyLabel_4.setText(_translate("shpCalCentroidDialog", "Result Path"))
        self.runPB.setText(_translate("shpCalCentroidDialog", "OK"))
        self.cancelPB.setText(_translate("shpCalCentroidDialog", "Cancel"))
from qfluentwidgets import BodyLabel, CardWidget, CheckBox, ComboBox, LineEdit, PushButton, ToolButton
import yoyirs_rc
