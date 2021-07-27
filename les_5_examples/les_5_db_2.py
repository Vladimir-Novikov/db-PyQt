# ---------------- Графический интерфейс пользователя. PyQt5

# Взаимодействие SQLAlchemy и PyQt.
# Пример использования SQLAlchemy + PyQt
import sys
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import sessionmaker
from PyQt5.QtWidgets import QTableView, QWidget, QApplication, QPushButton
from PyQt5 import QtCore
from alchemical_model import AlchemicalTableModel

# ------------- Создание и настройка SQLAlchemy-механизмов ------------------
eng = create_engine("sqlite:///:memory:")

Base = declarative_base()


class Car(Base):
    __tablename__ = "Cars"
    Id = Column(Integer, primary_key=True)
    Name = Column(String)
    Price = Column(Integer)


Base.metadata.bind = eng
Base.metadata.create_all()
Session = sessionmaker(bind=eng)
ses = Session()
ses.add_all(
    [
        Car(Id=1, Name="Audi", Price=52642),
        Car(Id=2, Name="Mercedes", Price=57127),
        Car(Id=3, Name="Skoda", Price=9000),
        Car(Id=4, Name="Volvo", Price=29000),
        Car(Id=5, Name="Bentley", Price=350000),
        Car(Id=6, Name="Citroen", Price=21000),
        Car(Id=7, Name="Hummer", Price=41400),
        Car(Id=8, Name="Volkswagen", Price=21600),
    ]
)
ses.commit()
rs = ses.query(Car).all()

# Простая печать выборки для демонстрации
for car in rs:
    print(car.Name, car.Price)


# ---------------------- Передача данных в PyQt-классы -----------------------
# Создание QTable Model/View
model = AlchemicalTableModel(
    ses,
    ses.query(Car),
    [  # Список кортежей, описывающих столбцы:
        # (заголовок, sqlalchemy-столбец, имя столбца, словарь доп. параметров).
        # Если sqlalchemy-столбец имеет имя, например, Car.Name,
        # тогда имя столбца в кортеже нужно указывать 'Name'.
        # Car.Name будет использоваться для установки и сортировки данных,
        # 'Name' - для получения данных.
        ("Car Name", Car.Name, "Name", {"editable": True}),
        ("Price", Car.Price, "Price", {"editable": True}),
    ],
)


def print_data():
    rs = ses.query(Car).all()
    for car in rs:
        print(car.Name, car.Price)


app = QApplication(sys.argv)
widget = QWidget()
widget.setMinimumSize(QtCore.QSize(328, 228))
table = QTableView(widget)
# Назначение модели данных виджету таблицы
table.setModel(model)
button = QPushButton(widget)
button.clicked.connect(print_data)
widget.show()
sys.exit(app.exec_())
