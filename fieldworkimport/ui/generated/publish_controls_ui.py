# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'publish_controls_ui.ui'
#
# Created by: PyQt5 UI code generator 5.15.10
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_PublishControlsDialog(object):
    def setupUi(self, PublishControlsDialog):
        PublishControlsDialog.setObjectName("PublishControlsDialog")
        PublishControlsDialog.setWindowModality(QtCore.Qt.WindowModal)
        PublishControlsDialog.resize(400, 567)
        self.verticalLayout = QtWidgets.QVBoxLayout(PublishControlsDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtWidgets.QLabel(PublishControlsDialog)
        self.label.setWordWrap(True)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.label_2 = QtWidgets.QLabel(PublishControlsDialog)
        self.label_2.setObjectName("label_2")
        self.verticalLayout.addWidget(self.label_2)
        self.line = QtWidgets.QFrame(PublishControlsDialog)
        self.line.setFrameShape(QtWidgets.QFrame.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line.setObjectName("line")
        self.verticalLayout.addWidget(self.line)
        self.formLayout_2 = QtWidgets.QFormLayout()
        self.formLayout_2.setObjectName("formLayout_2")
        self.label_3 = QtWidgets.QLabel(PublishControlsDialog)
        self.label_3.setObjectName("label_3")
        self.formLayout_2.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label_3)
        self.fieldwork_input = QgsFeaturePickerWidget(PublishControlsDialog)
        self.fieldwork_input.setObjectName("fieldwork_input")
        self.formLayout_2.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.fieldwork_input)
        self.verticalLayout.addLayout(self.formLayout_2)
        self.scrollArea = QtWidgets.QScrollArea(PublishControlsDialog)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 380, 428))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.verticalLayout.addWidget(self.scrollArea)
        self.buttonBox = QtWidgets.QDialogButtonBox(PublishControlsDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(PublishControlsDialog)
        self.buttonBox.accepted.connect(PublishControlsDialog.accept) # type: ignore
        self.buttonBox.rejected.connect(PublishControlsDialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(PublishControlsDialog)

    def retranslateUi(self, PublishControlsDialog):
        _translate = QtCore.QCoreApplication.translate
        PublishControlsDialog.setWindowTitle(_translate("PublishControlsDialog", "Publish Controls"))
        self.label.setText(_translate("PublishControlsDialog", "Below is a list of new control points found and matched from this set of fieldwork data."))
        self.label_2.setText(_translate("PublishControlsDialog", "Please enter in the fields so that they can be published."))
        self.label_3.setText(_translate("PublishControlsDialog", "Selected Fieldwork"))
from qgsfeaturepickerwidget import QgsFeaturePickerWidget
