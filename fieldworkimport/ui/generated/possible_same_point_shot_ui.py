# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'possible_same_point_shot_ui.ui'
#
# Created by: PyQt5 UI code generator 5.15.10
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_PossibleSamePointShotDialog(object):
    def setupUi(self, PossibleSamePointShotDialog):
        PossibleSamePointShotDialog.setObjectName("PossibleSamePointShotDialog")
        PossibleSamePointShotDialog.setWindowModality(QtCore.Qt.WindowModal)
        PossibleSamePointShotDialog.resize(601, 449)
        self.verticalLayout = QtWidgets.QVBoxLayout(PossibleSamePointShotDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.groupBox = QtWidgets.QGroupBox(PossibleSamePointShotDialog)
        self.groupBox.setObjectName("groupBox")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.groupBox)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.formLayout = QtWidgets.QFormLayout()
        self.formLayout.setObjectName("formLayout")
        self.label_10 = QtWidgets.QLabel(self.groupBox)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.label_10.setFont(font)
        self.label_10.setObjectName("label_10")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label_10)
        self.p1_desc_text = QtWidgets.QLabel(self.groupBox)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.p1_desc_text.setFont(font)
        self.p1_desc_text.setObjectName("p1_desc_text")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.p1_desc_text)
        self.label_8 = QtWidgets.QLabel(self.groupBox)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.label_8.setFont(font)
        self.label_8.setObjectName("label_8")
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.LabelRole, self.label_8)
        self.residuals_text = QtWidgets.QLabel(self.groupBox)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.residuals_text.setFont(font)
        self.residuals_text.setObjectName("residuals_text")
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.FieldRole, self.residuals_text)
        self.label_7 = QtWidgets.QLabel(self.groupBox)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.label_7.setFont(font)
        self.label_7.setObjectName("label_7")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.label_7)
        self.p2_desc_text = QtWidgets.QLabel(self.groupBox)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.p2_desc_text.setFont(font)
        self.p2_desc_text.setObjectName("p2_desc_text")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.p2_desc_text)
        self.verticalLayout_2.addLayout(self.formLayout)
        self.line = QtWidgets.QFrame(self.groupBox)
        self.line.setFrameShape(QtWidgets.QFrame.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line.setObjectName("line")
        self.verticalLayout_2.addWidget(self.line)
        self.label = QtWidgets.QLabel(self.groupBox)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.label.setFont(font)
        self.label.setObjectName("label")
        self.verticalLayout_2.addWidget(self.label)
        self.do_nothing_radio = QtWidgets.QRadioButton(self.groupBox)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.do_nothing_radio.setFont(font)
        self.do_nothing_radio.setChecked(True)
        self.do_nothing_radio.setObjectName("do_nothing_radio")
        self.verticalLayout_2.addWidget(self.do_nothing_radio)
        self.label_5 = QtWidgets.QLabel(self.groupBox)
        font = QtGui.QFont()
        font.setPointSize(8)
        self.label_5.setFont(font)
        self.label_5.setObjectName("label_5")
        self.verticalLayout_2.addWidget(self.label_5)
        self.keep_p1_radio = QtWidgets.QRadioButton(self.groupBox)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.keep_p1_radio.setFont(font)
        self.keep_p1_radio.setObjectName("keep_p1_radio")
        self.verticalLayout_2.addWidget(self.keep_p1_radio)
        self.keep_p1_help_text = QtWidgets.QLabel(self.groupBox)
        font = QtGui.QFont()
        font.setPointSize(8)
        self.keep_p1_help_text.setFont(font)
        self.keep_p1_help_text.setObjectName("keep_p1_help_text")
        self.verticalLayout_2.addWidget(self.keep_p1_help_text)
        self.keep_p2_radio = QtWidgets.QRadioButton(self.groupBox)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.keep_p2_radio.setFont(font)
        self.keep_p2_radio.setObjectName("keep_p2_radio")
        self.verticalLayout_2.addWidget(self.keep_p2_radio)
        self.keep_p2_help_text = QtWidgets.QLabel(self.groupBox)
        font = QtGui.QFont()
        font.setPointSize(8)
        self.keep_p2_help_text.setFont(font)
        self.keep_p2_help_text.setObjectName("keep_p2_help_text")
        self.verticalLayout_2.addWidget(self.keep_p2_help_text)
        self.recalculate_new_point_radio = QtWidgets.QRadioButton(self.groupBox)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.recalculate_new_point_radio.setFont(font)
        self.recalculate_new_point_radio.setObjectName("recalculate_new_point_radio")
        self.verticalLayout_2.addWidget(self.recalculate_new_point_radio)
        self.recalculate_help_text = QtWidgets.QLabel(self.groupBox)
        font = QtGui.QFont()
        font.setPointSize(8)
        self.recalculate_help_text.setFont(font)
        self.recalculate_help_text.setWordWrap(True)
        self.recalculate_help_text.setObjectName("recalculate_help_text")
        self.verticalLayout_2.addWidget(self.recalculate_help_text)
        self.verticalLayout.addWidget(self.groupBox)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.buttonBox = QtWidgets.QDialogButtonBox(PossibleSamePointShotDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Save)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(PossibleSamePointShotDialog)
        self.buttonBox.accepted.connect(PossibleSamePointShotDialog.accept) # type: ignore
        self.buttonBox.rejected.connect(PossibleSamePointShotDialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(PossibleSamePointShotDialog)

    def retranslateUi(self, PossibleSamePointShotDialog):
        _translate = QtCore.QCoreApplication.translate
        PossibleSamePointShotDialog.setWindowTitle(_translate("PossibleSamePointShotDialog", "Possible same-point shot"))
        self.groupBox.setTitle(_translate("PossibleSamePointShotDialog", "Possible same-point shot"))
        self.label_10.setText(_translate("PossibleSamePointShotDialog", "(Point 1)"))
        self.p1_desc_text.setText(_translate("PossibleSamePointShotDialog", "{{p1_name}} - {{p1_description}}"))
        self.label_8.setText(_translate("PossibleSamePointShotDialog", "(Residuals)"))
        self.residuals_text.setText(_translate("PossibleSamePointShotDialog", "{{residual_east}}, {{residual_north}}, {{residual_elevation}}"))
        self.label_7.setText(_translate("PossibleSamePointShotDialog", "(Point 2)"))
        self.p2_desc_text.setText(_translate("PossibleSamePointShotDialog", "{{p2_name}} - {{p2_description}}"))
        self.label.setText(_translate("PossibleSamePointShotDialog", "What do you want to do?"))
        self.do_nothing_radio.setText(_translate("PossibleSamePointShotDialog", "Nothing"))
        self.label_5.setText(_translate("PossibleSamePointShotDialog", "Leave both points as they are."))
        self.keep_p1_radio.setText(_translate("PossibleSamePointShotDialog", "Keep {{p1_name}}"))
        self.keep_p1_help_text.setText(_translate("PossibleSamePointShotDialog", "{{p2_name}} becomes the child of {{p1_name}}, {{p1_name}} is untouched."))
        self.keep_p2_radio.setText(_translate("PossibleSamePointShotDialog", "Keep {{p2_name}}"))
        self.keep_p2_help_text.setText(_translate("PossibleSamePointShotDialog", "{{p1_name}} becomes the child of {{p2_name}}, {{p2_name}} is untouched."))
        self.recalculate_new_point_radio.setText(_translate("PossibleSamePointShotDialog", "Recalculate as a new point"))
        self.recalculate_help_text.setText(_translate("PossibleSamePointShotDialog", "{{p1_name}} and {{p2_name}}, and all their children, are used to calculate a new shot. {{p1_name}} and {{p2_name}} become children of this shot."))
