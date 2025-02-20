# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'recalculate_shot_ui.ui'
#
# Created by: PyQt5 UI code generator 5.15.10
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_RecalculateShotDialog(object):
    def setupUi(self, RecalculateShotDialog):
        RecalculateShotDialog.setObjectName("RecalculateShotDialog")
        RecalculateShotDialog.resize(636, 239)
        self.verticalLayout = QtWidgets.QVBoxLayout(RecalculateShotDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.treeWidget = QtWidgets.QTreeWidget(RecalculateShotDialog)
        self.treeWidget.setObjectName("treeWidget")
        self.verticalLayout.addWidget(self.treeWidget)
        self.avg_coord_text = QtWidgets.QLabel(RecalculateShotDialog)
        self.avg_coord_text.setObjectName("avg_coord_text")
        self.verticalLayout.addWidget(self.avg_coord_text)
        self.buttonBox = QtWidgets.QDialogButtonBox(RecalculateShotDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Save)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(RecalculateShotDialog)
        self.buttonBox.accepted.connect(RecalculateShotDialog.accept) # type: ignore
        self.buttonBox.rejected.connect(RecalculateShotDialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(RecalculateShotDialog)

    def retranslateUi(self, RecalculateShotDialog):
        _translate = QtCore.QCoreApplication.translate
        RecalculateShotDialog.setWindowTitle(_translate("RecalculateShotDialog", "Recalculate Shot"))
        self.treeWidget.headerItem().setText(0, _translate("RecalculateShotDialog", "Point"))
        self.treeWidget.headerItem().setText(1, _translate("RecalculateShotDialog", "Description"))
        self.treeWidget.headerItem().setText(2, _translate("RecalculateShotDialog", "Easting"))
        self.treeWidget.headerItem().setText(3, _translate("RecalculateShotDialog", "Northing"))
        self.treeWidget.headerItem().setText(4, _translate("RecalculateShotDialog", "Elevation"))
        self.treeWidget.headerItem().setText(5, _translate("RecalculateShotDialog", "Residual E"))
        self.treeWidget.headerItem().setText(6, _translate("RecalculateShotDialog", "Residual N"))
        self.treeWidget.headerItem().setText(7, _translate("RecalculateShotDialog", "Residual El"))
        self.avg_coord_text.setText(_translate("RecalculateShotDialog", "Avg: {{easting}}, {{northing}}, {{elevation}}"))
