import sys

from PyQt5 import QtSql, QtWidgets, uic
from PyQt5.QtSql import QSqlQuery, QSqlTableModel

Form, _ = uic.loadUiType("admin.ui")


class Ui(QtWidgets.QDialog, Form):
    def __init__(self):
        super(Ui, self).__init__()
        self.setupUi(self)
        self.pushButton.clicked.connect(self.get_file_path)  # обработчик нажатия кнопки
        self.comboBox.currentTextChanged.connect(self.get_item_combo_box)  # обработчик comboBox
        self.pushButton_2.clicked.connect(self.get_info)  # обработчик нажатия второй кнопки

    def db_connect(self, filename):  # подключаемся к БД
        conn = QtSql.QSqlDatabase.addDatabase("QSQLITE")
        conn.setDatabaseName(filename)
        conn.open()
        tables_list = conn.tables()[:]  # список всех таблиц в выбранной БД
        if "sqlite_sequence" in tables_list:
            tables_list.remove("sqlite_sequence")  # удаляем служебную таблицу
        self.combo_box(tables_list)

    def combo_box(self, tables_list):
        self.comboBox.clear()  # при смене БД комбобокс очищаем
        self.comboBox.addItems(tables_list)

    def get_item_combo_box(
        self,
    ):  # получаем имя текущей таблицы и передаем его в загрузку в tableView
        current_db = self.comboBox.currentText()
        self.load_table(current_db)

    def load_table(self, current_db):
        model = QSqlTableModel()
        model.setTable(f"{current_db}")
        model.setEditStrategy(QSqlTableModel.OnFieldChange)  # указываем стратегию (можно менять данные)
        self.tableView.setModel(model)
        model.select()

    def get_file_path(self):
        filename = QtWidgets.QFileDialog.getOpenFileName(self, "Выберите файл БД", "", "*.db *.sqlite *.sqlite3")
        if filename[0]:  # если нажата кнопка ОТМЕНА, то будет пустой путь
            self.label.setText((filename[0]))
            self.db_connect(filename[0])

    def get_info(self):
        query = QSqlQuery()
        query = """
            SELECT users.login as 'Пользователь', count(from_user_id) as 'Сообщений' FROM messages inner join users on messages.from_user_id = users.id GROUP BY from_user_id;"""
        q = QSqlQuery(query)
        model = QSqlTableModel()
        model.setQuery(q)
        self.tableView.setModel(model)
        model.select()


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    w = Ui()
    w.show()
    sys.exit(app.exec())
