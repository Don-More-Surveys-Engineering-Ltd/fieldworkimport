# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'new_form_ui.ui'
#
# Created by: PyQt5 UI code generator 5.15.10
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_ImportDialog(object):
    def setupUi(self, ImportDialog):
        ImportDialog.setObjectName("ImportDialog")
        ImportDialog.resize(772, 235)
        ImportDialog.setModal(False)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(ImportDialog)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.groupBox = QtWidgets.QGroupBox(ImportDialog)
        self.groupBox.setObjectName("groupBox")
        self.formLayout_5 = QtWidgets.QFormLayout(self.groupBox)
        self.formLayout_5.setObjectName("formLayout_5")
        self.label_25 = QtWidgets.QLabel(self.groupBox)
        self.label_25.setObjectName("label_25")
        self.formLayout_5.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.label_25)
        self.crdb_file_input = QgsFileWidget(self.groupBox)
        self.crdb_file_input.setObjectName("crdb_file_input")
        self.formLayout_5.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.crdb_file_input)
        self.label_26 = QtWidgets.QLabel(self.groupBox)
        self.label_26.setObjectName("label_26")
        self.formLayout_5.setWidget(2, QtWidgets.QFormLayout.LabelRole, self.label_26)
        self.rw5_file_input = QgsFileWidget(self.groupBox)
        self.rw5_file_input.setObjectName("rw5_file_input")
        self.formLayout_5.setWidget(2, QtWidgets.QFormLayout.FieldRole, self.rw5_file_input)
        self.label_27 = QtWidgets.QLabel(self.groupBox)
        self.label_27.setObjectName("label_27")
        self.formLayout_5.setWidget(3, QtWidgets.QFormLayout.LabelRole, self.label_27)
        self.sum_file_input = QgsFileWidget(self.groupBox)
        self.sum_file_input.setObjectName("sum_file_input")
        self.formLayout_5.setWidget(3, QtWidgets.QFormLayout.FieldRole, self.sum_file_input)
        self.label_28 = QtWidgets.QLabel(self.groupBox)
        self.label_28.setObjectName("label_28")
        self.formLayout_5.setWidget(4, QtWidgets.QFormLayout.LabelRole, self.label_28)
        self.ref_file_input = QgsFileWidget(self.groupBox)
        self.ref_file_input.setObjectName("ref_file_input")
        self.formLayout_5.setWidget(4, QtWidgets.QFormLayout.FieldRole, self.ref_file_input)
        self.label_29 = QtWidgets.QLabel(self.groupBox)
        self.label_29.setObjectName("label_29")
        self.formLayout_5.setWidget(5, QtWidgets.QFormLayout.LabelRole, self.label_29)
        self.loc_file_input = QgsFileWidget(self.groupBox)
        self.loc_file_input.setObjectName("loc_file_input")
        self.formLayout_5.setWidget(5, QtWidgets.QFormLayout.FieldRole, self.loc_file_input)
        self.label_30 = QtWidgets.QLabel(self.groupBox)
        self.label_30.setObjectName("label_30")
        self.formLayout_5.setWidget(6, QtWidgets.QFormLayout.LabelRole, self.label_30)
        self.fieldrun_input = QgsFeaturePickerWidget(self.groupBox)
        self.fieldrun_input.setAllowNull(True)
        self.fieldrun_input.setShowBrowserButtons(False)
        self.fieldrun_input.setObjectName("fieldrun_input")
        self.formLayout_5.setWidget(6, QtWidgets.QFormLayout.FieldRole, self.fieldrun_input)
        self.verticalLayout_2.addWidget(self.groupBox)
        self.buttonBox = QtWidgets.QDialogButtonBox(ImportDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout_2.addWidget(self.buttonBox)

        self.retranslateUi(ImportDialog)
        self.buttonBox.accepted.connect(ImportDialog.accept) # type: ignore
        self.buttonBox.rejected.connect(ImportDialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(ImportDialog)

    def retranslateUi(self, ImportDialog):
        _translate = QtCore.QCoreApplication.translate
        ImportDialog.setWindowTitle(_translate("ImportDialog", "Import Fieldwork"))
        self.groupBox.setTitle(_translate("ImportDialog", "Fieldwork Setup"))
        self.label_25.setText(_translate("ImportDialog", "CRDB File*"))
        self.crdb_file_input.setFilter(_translate("ImportDialog", "CRDB file (*.crdb)"))
        self.label_26.setText(_translate("ImportDialog", "RW5 File*"))
        self.rw5_file_input.setFilter(_translate("ImportDialog", "RW5 file (*.rw5)"))
        self.label_27.setText(_translate("ImportDialog", "SUM File"))
        self.sum_file_input.setFilter(_translate("ImportDialog", "SUM file (*.sum)"))
        self.label_28.setText(_translate("ImportDialog", "REF File"))
        self.ref_file_input.setFilter(_translate("ImportDialog", "REF file (*.ref)"))
        self.label_29.setText(_translate("ImportDialog", "LOC File"))
        self.loc_file_input.setFilter(_translate("ImportDialog", "LOC file (*.loc)"))
        self.label_30.setText(_translate("ImportDialog", "Fieldrun"))
from qgsfeaturepickerwidget import QgsFeaturePickerWidget
from qgsfilewidget import QgsFileWidget
