# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'match_to_controls_ui.ui'
#
# Created by: PyQt5 UI code generator 5.15.10
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_MatchControlPoints(object):
    def setupUi(self, MatchControlPoints):
        MatchControlPoints.setObjectName("MatchControlPoints")
        MatchControlPoints.setWindowModality(QtCore.Qt.WindowModal)
        MatchControlPoints.resize(582, 690)
        self.verticalLayout = QtWidgets.QVBoxLayout(MatchControlPoints)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtWidgets.QLabel(MatchControlPoints)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.scrollArea = QtWidgets.QScrollArea(MatchControlPoints)
        self.scrollArea.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.scrollArea.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.scrollArea.setLineWidth(1)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.scrollAreaContents = QtWidgets.QWidget()
        self.scrollAreaContents.setGeometry(QtCore.QRect(0, 0, 562, 621))
        self.scrollAreaContents.setObjectName("scrollAreaContents")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.scrollAreaContents)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.scrollArea.setWidget(self.scrollAreaContents)
        self.verticalLayout.addWidget(self.scrollArea)
        self.buttonBox = QtWidgets.QDialogButtonBox(MatchControlPoints)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(MatchControlPoints)
        self.buttonBox.accepted.connect(MatchControlPoints.accept) # type: ignore
        self.buttonBox.rejected.connect(MatchControlPoints.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(MatchControlPoints)

    def retranslateUi(self, MatchControlPoints):
        _translate = QtCore.QCoreApplication.translate
        MatchControlPoints.setWindowTitle(_translate("MatchControlPoints", "Match Control Points"))
        self.label.setText(_translate("MatchControlPoints", "Match the fieldwork shots below to the correct control point."))
