# Взаимодействие SQLAlchemy и PyQt.
# Класс модели данных, связываемой с выборкой SQLAlchemy
# Original code:
# (c) 2013 Mark Harviston, BSD License
"""
Qt data models that bind to SQLAlchemy queries
"""
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QAbstractTableModel, QVariant, Qt


class AlchemicalTableModel(QAbstractTableModel):
    """
    A Qt Table Model that binds to a SQL Alchemy query
    Example:
    >>> model = AlchemicalTableModel(Session, [('Name', Entity.name)])
    >>> table = QTableView(parent)
    >>> table.setModel(model)
    """

    def __init__(self, session, query, columns):
        super(AlchemicalTableModel, self).__init__()
        self.session = session
        self.fields = columns
        self.query = query
        self.results = None
        self.count = None
        self.sort = None
        self.filter = None
        self.refresh()

    def headerData(self, col, orientation, role):
        """ Данные заголовков для указанной роли role и столбца col """
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return QVariant(self.fields[col][0])
        return QVariant()

    def setFilter(self, filter):
        """ Установка/очистка фильтра данных (для очистки filter=None). """
        self.filter = filter
        self.refresh()

    def refresh(self):
        """ Пересчет атрибутов self.results и self.count """
        self.layoutAboutToBeChanged.emit()

        q = self.query
        if self.sort is not None:
            order, col = self.sort
            col = self.fields[col][1]
            if order == Qt.DescendingOrder:
                col = col.desc()
        else:
            col = None
        if self.filter is not None:
            q = q.filter(self.filter)
        q = q.order_by(col)
        self.results = q.all()
        self.count = q.count()
        self.layoutChanged.emit()

    def flags(self, index):
        """ Набор флагов для элемента с указанным индексом index """
        _flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if self.sort is not None:
            order, col = self.sort
            if self.fields[col][3].get("dnd", False) and index.column() == col:
                _flags |= Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled
        if self.fields[index.column()][3].get("editable", False):
            _flags |= Qt.ItemIsEditable
        return _flags

    def supportedDropActions(self):
        """ Поддерживаемые drop-действия при drag&drop операциях """
        return Qt.MoveAction

    def dropMimeData(self, data, action, row, col, parent):
        """ Управляет данными data в drag&drop операциях при событии action """
        if action != Qt.MoveAction:
            return
        return False

    def rowCount(self, parent):
        """ Количество строк """
        return self.count or 0

    def columnCount(self, parent):
        """ Количество количество столбцов/полей """
        return len(self.fields)

    def data(self, index, role):

        """ Получение данных из запроса """
        if not index.isValid():
            return QVariant()
        elif role not in (Qt.DisplayRole, Qt.EditRole):
            return QVariant()
        row = self.results[index.row()]
        name = self.fields[index.column()][2]
        return str(getattr(row, name))

    def setData(self, index, value, role=None):
        """ Установка данных в связанном запросе """
        row = self.results[index.row()]
        name = self.fields[index.column()][2]
        try:
            setattr(row, name, value)
            self.session.commit()
        except Exception as ex:
            QMessageBox.critical(None, "SQL Error", str(ex))
            return False
        else:
            self.dataChanged.emit(index, index)
            return True

    def sort(self, col, order):
        """ Сортировка таблицы по указанному номеру столбца. """
        self.sort = order, col
        self.refresh()
