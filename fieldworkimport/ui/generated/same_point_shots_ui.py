# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'same_point_shots_ui.ui'
#
# Created by: PyQt5 UI code generator 5.15.4
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_SamePointShotsDialog(object):
    def setupUi(self, SamePointShotsDialog):
        SamePointShotsDialog.setObjectName("SamePointShotsDialog")
        SamePointShotsDialog.resize(963, 656)
        self.verticalLayout = QtWidgets.QVBoxLayout(SamePointShotsDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.groupBox = QtWidgets.QGroupBox(SamePointShotsDialog)
        self.groupBox.setObjectName("groupBox")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.groupBox)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.tolerance_text = QtWidgets.QLabel(self.groupBox)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.tolerance_text.setFont(font)
        self.tolerance_text.setObjectName("tolerance_text")
        self.verticalLayout_2.addWidget(self.tolerance_text)
        self.label_2 = QtWidgets.QLabel(self.groupBox)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.label_2.setFont(font)
        self.label_2.setObjectName("label_2")
        self.verticalLayout_2.addWidget(self.label_2)
        self.tree_widget = QtWidgets.QTreeWidget(self.groupBox)
        self.tree_widget.setObjectName("tree_widget")
        self.tree_widget.header().setHighlightSections(False)
        self.verticalLayout_2.addWidget(self.tree_widget)
        self.verticalLayout.addWidget(self.groupBox)
        self.buttonBox = QtWidgets.QDialogButtonBox(SamePointShotsDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Abort|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(SamePointShotsDialog)
        self.buttonBox.accepted.connect(SamePointShotsDialog.accept)
        self.buttonBox.rejected.connect(SamePointShotsDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(SamePointShotsDialog)

    def retranslateUi(self, SamePointShotsDialog):
        _translate = QtCore.QCoreApplication.translate
        SamePointShotsDialog.setWindowTitle(_translate("SamePointShotsDialog", "Merge same point shots."))
        self.groupBox.setTitle(_translate("SamePointShotsDialog", "Merge Same Point Shots"))
        self.tolerance_text.setText(_translate("SamePointShotsDialog", "The groups of points below are groups of points that fall within the same point tolerance (which is {{same_point_tolerance}})."))
        self.label_2.setText(_translate("SamePointShotsDialog", "After clicking OK, new points will be created as avergaes of the point groups."))
        self.tree_widget.headerItem().setText(0, _translate("SamePointShotsDialog", "Point/Code"))
        self.tree_widget.headerItem().setText(1, _translate("SamePointShotsDialog", "Northing"))
        self.tree_widget.headerItem().setText(2, _translate("SamePointShotsDialog", "Easting"))
        self.tree_widget.headerItem().setText(3, _translate("SamePointShotsDialog", "Elevation"))
        self.tree_widget.headerItem().setText(4, _translate("SamePointShotsDialog", "Residual N"))
        self.tree_widget.headerItem().setText(5, _translate("SamePointShotsDialog", "Residual E"))
        self.tree_widget.headerItem().setText(6, _translate("SamePointShotsDialog", "Residual El"))
