from setuptools import setup

setup(
    name="admin_app",
    version="1.0",
    description="admin",
    author="Vladimir Novikov",
    author_email="vovasnew@mail.ru",
    install_requires=[
        "PyQt5==5.15.4",
    ],
    include_package_data=True,
    packages=["src"],
)
